from __future__ import annotations

import mimetypes
import re
import uuid
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.management.base import BaseCommand

from shop.file_utils import infer_file_kind
from shop.models import (
    Brand,
    Group,
    News,
    NewsAttachment,
    Product,
    ProductCertificate,
    ProductDocument,
    ProductGalleryItem,
    ProductMedia,
    Sert,
    Slider,
)


REMOTE_MAX_BYTES = 100 * 1024 * 1024
REMOTE_TIMEOUT_SECONDS = 30


def is_remote_url(value: str | None) -> bool:
    parsed = urlparse(str(value or "").strip())
    return parsed.scheme in {"http", "https"}


def filename_from_response(url: str, response) -> str:
    content_disposition = response.headers.get("Content-Disposition", "")
    match = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', content_disposition, flags=re.IGNORECASE)
    if match:
        filename = unquote(match.group(1)).strip()
        if filename:
            return Path(filename).name
    return Path(unquote(urlparse(url).path)).name or f"remote-{uuid.uuid4().hex[:8]}"


def download_remote_file(url: str, folder_name: str) -> dict:
    media_root = Path(settings.MEDIA_ROOT)
    target_dir = media_root / "admin_uploads" / folder_name
    target_dir.mkdir(parents=True, exist_ok=True)

    request = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; NovotechMediaLocalizer/1.0)"},
    )
    with urlopen(request, timeout=REMOTE_TIMEOUT_SECONDS) as response:
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > REMOTE_MAX_BYTES:
            raise ValueError(f"remote file is larger than {REMOTE_MAX_BYTES // 1024 // 1024} MB")

        original_name = filename_from_response(url, response)
        storage_path = target_dir / f"{uuid.uuid4().hex}{Path(original_name).suffix}"
        downloaded = 0

        with storage_path.open("wb") as destination:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                downloaded += len(chunk)
                if downloaded > REMOTE_MAX_BYTES:
                    storage_path.unlink(missing_ok=True)
                    raise ValueError(f"remote file is larger than {REMOTE_MAX_BYTES // 1024 // 1024} MB")
                destination.write(chunk)

    relative_path = storage_path.relative_to(media_root).as_posix()
    mime_type = mimetypes.guess_type(original_name)[0] or mimetypes.guess_type(str(storage_path))[0] or "application/octet-stream"

    return {
        "storage_path": str(storage_path),
        "url": f"{settings.MEDIA_URL}{relative_path}",
        "mime_type": mime_type,
        "size_bytes": storage_path.stat().st_size,
        "title": original_name,
    }


class Command(BaseCommand):
    help = "Download remote media URLs to local MEDIA_ROOT and replace database links with local /static/ URLs."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without downloading or saving.")

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"]
        self.changed = 0
        self.failed = 0

        self.localize_simple_field(Brand.objects.exclude(media__isnull=True).exclude(media__exact=""), "media", "brands", "Brand media")
        self.localize_simple_field(Group.objects.exclude(media__isnull=True).exclude(media__exact=""), "media", "groups", "Group media")
        self.localize_simple_field(Slider.objects.exclude(image__isnull=True).exclude(image__exact=""), "image", "slider", "Slider image")

        self.localize_file_model(ProductMedia.objects.all(), "product_media", "Product media", kind_field="media_kind")
        self.localize_file_model(ProductGalleryItem.objects.all(), "product_gallery", "Product gallery", kind_field="file_kind")
        self.localize_file_model(ProductDocument.objects.all(), "product_documents", "Product document")
        self.localize_file_model(ProductCertificate.objects.all(), "product_certificates", "Product certificate")
        self.localize_file_model(NewsAttachment.objects.all(), "news_attachments", "News attachment")
        self.localize_file_model(Sert.objects.all(), "serts", "Sert file")

        self.localize_json_media(Product.objects.exclude(media__isnull=True), "media", "products", "Product media JSON")
        self.localize_json_media(News.objects.exclude(media__isnull=True), "media", "news", "News media JSON")

        self.stdout.write(self.style.SUCCESS(f"Done. Changed: {self.changed}. Failed: {self.failed}. Dry-run: {self.dry_run}."))

    def localize_url(self, url: str, folder_name: str, label: str):
        if self.dry_run:
            self.stdout.write(f"[dry-run] {label}: {url}")
            return {
                "storage_path": "",
                "url": url,
                "mime_type": mimetypes.guess_type(urlparse(url).path)[0] or "application/octet-stream",
                "size_bytes": 0,
                "title": Path(urlparse(url).path).name or "remote file",
            }
        return download_remote_file(url, folder_name)

    def localize_simple_field(self, queryset, field_name: str, folder_name: str, label: str):
        for obj in queryset.iterator():
            url = getattr(obj, field_name)
            if not is_remote_url(url):
                continue
            item_label = f"{label} #{obj.pk}"
            try:
                uploaded = self.localize_url(url, folder_name, item_label)
            except Exception as exc:
                self.failed += 1
                self.stderr.write(self.style.ERROR(f"{item_label}: failed to download {url}: {exc}"))
                continue
            if not self.dry_run:
                setattr(obj, field_name, uploaded["url"])
                obj.save(update_fields=[field_name])
            self.changed += 1
            self.stdout.write(self.style.SUCCESS(f"{item_label}: {url} -> {uploaded['url']}"))

    def localize_file_model(self, queryset, folder_name: str, label: str, kind_field: str | None = None):
        for obj in queryset.iterator():
            if not is_remote_url(obj.url):
                continue
            item_label = f"{label} #{obj.pk}"
            try:
                uploaded = self.localize_url(obj.url, folder_name, item_label)
            except Exception as exc:
                self.failed += 1
                self.stderr.write(self.style.ERROR(f"{item_label}: failed to download {obj.url}: {exc}"))
                continue
            if not self.dry_run:
                obj.storage_path = uploaded["storage_path"]
                obj.url = uploaded["url"]
                obj.mime_type = uploaded["mime_type"]
                obj.size_bytes = uploaded["size_bytes"]
                update_fields = ["storage_path", "url", "mime_type", "size_bytes"]
                if kind_field:
                    setattr(obj, kind_field, infer_file_kind(uploaded["mime_type"]))
                    update_fields.append(kind_field)
                obj.save(update_fields=update_fields)
            self.changed += 1
            self.stdout.write(self.style.SUCCESS(f"{item_label}: localized to {uploaded['url']}"))

    def localize_json_media(self, queryset, field_name: str, folder_name: str, label: str):
        for obj in queryset.iterator():
            value = getattr(obj, field_name)
            updated_value, changed = self.localize_json_value(value, folder_name, f"{label} #{obj.pk}")
            if not changed:
                continue
            if not self.dry_run:
                setattr(obj, field_name, updated_value)
                obj.save(update_fields=[field_name])
            self.changed += 1

    def localize_json_value(self, value, folder_name: str, label: str):
        if isinstance(value, list):
            changed = False
            updated_items = []
            for index, item in enumerate(value):
                updated_item, item_changed = self.localize_json_item(item, folder_name, f"{label}[{index}]")
                updated_items.append(updated_item)
                changed = changed or item_changed
            return updated_items, changed
        updated_item, changed = self.localize_json_item(value, folder_name, label)
        return updated_item, changed

    def localize_json_item(self, item, folder_name: str, label: str):
        if isinstance(item, str):
            if not is_remote_url(item):
                return item, False
            try:
                uploaded = self.localize_url(item, folder_name, label)
            except Exception as exc:
                self.failed += 1
                self.stderr.write(self.style.ERROR(f"{label}: failed to download {item}: {exc}"))
                return item, False
            self.stdout.write(self.style.SUCCESS(f"{label}: {item} -> {uploaded['url']}"))
            return uploaded["url"], True

        if isinstance(item, dict):
            url = item.get("url") or item.get("src") or item.get("path")
            if not is_remote_url(url):
                return item, False
            try:
                uploaded = self.localize_url(url, folder_name, label)
            except Exception as exc:
                self.failed += 1
                self.stderr.write(self.style.ERROR(f"{label}: failed to download {url}: {exc}"))
                return item, False
            updated = item.copy()
            updated["url"] = uploaded["url"]
            updated["storage_path"] = uploaded["storage_path"]
            updated["mime_type"] = uploaded["mime_type"]
            updated["size_bytes"] = uploaded["size_bytes"]
            self.stdout.write(self.style.SUCCESS(f"{label}: {url} -> {uploaded['url']}"))
            return updated, True

        return item, False
