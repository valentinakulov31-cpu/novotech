import mimetypes
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.db.models import Q

from shop.admin_media_helpers import (
    media_item_matches,
    resolve_media_storage_path,
    strip_asset_from_json_media,
)
from shop.models import (
    Brand,
    ContactInfo,
    Group,
    MediaLibrary,
    News,
    NewsAttachment,
    Product,
    ProductCertificate,
    ProductGalleryItem,
    ProductMedia,
    SharedProductGalleryItem,
    Sert,
    Slider,
)


def build_media_match_q(asset_url: str | None, asset_storage_path: str | None):
    match_q = Q()
    if asset_url:
        match_q |= Q(url=asset_url)
    if asset_storage_path:
        normalized_path = resolve_media_storage_path(storage_path=asset_storage_path)
        match_q |= Q(storage_path=asset_storage_path)
        if normalized_path and normalized_path != asset_storage_path:
            match_q |= Q(storage_path=normalized_path)
    return match_q


def delete_media_asset(asset_url: str | None, asset_storage_path: str | None) -> dict:
    normalized_storage_path = resolve_media_storage_path(url=asset_url, storage_path=asset_storage_path)
    result = {
        "deleted_rows": {
            "product_media": 0,
            "product_gallery": 0,
            "shared_product_gallery": 0,
            "product_certificates": 0,
            "news_attachments": 0,
            "serts": 0,
            "library_refs": 0,
        },
        "cleared_fields": {
            "brands": 0,
            "groups": 0,
            "sliders": 0,
            "contacts": 0,
        },
        "updated_products": 0,
        "updated_news": 0,
        "affected_product_count": 0,
        "file_deleted": False,
    }

    with transaction.atomic():
        match_q = build_media_match_q(asset_url, normalized_storage_path or asset_storage_path)

        product_media_qs = ProductMedia.objects.filter(match_q)
        affected_product_ids = set(product_media_qs.values_list("product_id", flat=True))
        result["deleted_rows"]["product_media"] = product_media_qs.count()
        product_media_qs.delete()

        product_gallery_qs = ProductGalleryItem.objects.filter(match_q)
        affected_product_ids.update(product_gallery_qs.values_list("product_id", flat=True))
        result["deleted_rows"]["product_gallery"] = product_gallery_qs.count()
        product_gallery_qs.delete()

        shared_gallery_qs = SharedProductGalleryItem.objects.filter(match_q)
        result["deleted_rows"]["shared_product_gallery"] = shared_gallery_qs.count()
        shared_gallery_qs.delete()

        product_cert_qs = ProductCertificate.objects.filter(match_q)
        affected_product_ids.update(product_cert_qs.values_list("product_id", flat=True))
        result["deleted_rows"]["product_certificates"] = product_cert_qs.count()
        product_cert_qs.delete()

        news_attachment_qs = NewsAttachment.objects.filter(match_q)
        result["deleted_rows"]["news_attachments"] = news_attachment_qs.count()
        news_attachment_qs.delete()

        sert_qs = Sert.objects.filter(match_q)
        result["deleted_rows"]["serts"] = sert_qs.count()
        sert_qs.delete()

        for brand in Brand.objects.filter(media=asset_url):
            brand.media = None
            brand.save(update_fields=["media"])
            result["cleared_fields"]["brands"] += 1

        for group in Group.objects.filter(media=asset_url):
            group.media = None
            group.save(update_fields=["media"])
            result["cleared_fields"]["groups"] += 1

        for slider in Slider.objects.filter(image=asset_url):
            slider.image = None
            slider.save(update_fields=["image"])
            result["cleared_fields"]["sliders"] += 1

        for news in News.objects.all():
            current_media = news.media
            new_media = None
            if media_item_matches(current_media, asset_url, normalized_storage_path or asset_storage_path):
                new_media = None
            elif isinstance(current_media, list):
                stripped = strip_asset_from_json_media(current_media, asset_url, normalized_storage_path or asset_storage_path)
                new_media = stripped or None
            else:
                continue
            if new_media != current_media:
                news.media = new_media
                news.save(update_fields=["media"])
                result["updated_news"] += 1

        for product in Product.objects.all():
            current_media = product.media
            if media_item_matches(current_media, asset_url, normalized_storage_path or asset_storage_path):
                updated_media = None
            else:
                updated_media = strip_asset_from_json_media(current_media, asset_url, normalized_storage_path or asset_storage_path)
            if updated_media != current_media:
                product.media = updated_media
                product.save(update_fields=["media"])
                result["updated_products"] += 1
                affected_product_ids.add(product.pk)

        for contact in ContactInfo.objects.filter(Q(yandex_link=asset_url) | Q(gis_link=asset_url)):
            if contact.yandex_link == asset_url:
                contact.yandex_link = ""
            if contact.gis_link == asset_url:
                contact.gis_link = ""
            contact.save(update_fields=["yandex_link", "gis_link"])
            result["cleared_fields"]["contacts"] += 1

        library_qs = MediaLibrary.objects.filter(match_q)
        result["deleted_rows"]["library_refs"] = library_qs.count()
        library_qs.delete()

        if normalized_storage_path:
            file_path = Path(normalized_storage_path)
            if file_path.exists() and file_path.is_file():
                file_path.unlink()
                result["file_deleted"] = True

    result["affected_product_count"] = len(affected_product_ids)
    return result


def collect_unused_media_file_entries():
    media_root = Path(settings.MEDIA_ROOT)
    uploads_root = media_root / "admin_uploads"
    if not uploads_root.exists():
        return []

    referenced_paths = set()
    for model in (
        ProductMedia,
        ProductGalleryItem,
        SharedProductGalleryItem,
        ProductCertificate,
        NewsAttachment,
        Sert,
    ):
        for value in model.objects.exclude(storage_path__in=["", None]).values_list("storage_path", flat=True):
            referenced_paths.add(str(resolve_media_storage_path(storage_path=value)))

    results = []
    for file_path in uploads_root.rglob("*"):
        if not file_path.is_file():
            continue
        normalized = str(file_path)
        if normalized in referenced_paths:
            continue
        relative_path = file_path.relative_to(media_root).as_posix()
        url = f"{settings.MEDIA_URL}{relative_path}"
        mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        results.append(
            {
                "asset_key": f"path::{normalized}",
                "url": url,
                "storage_path": normalized,
                "title": file_path.name,
                "mime_type": mime_type,
                "size_bytes": file_path.stat().st_size,
                "kind": "image" if mime_type.startswith("image/") else "document",
                "is_local": True,
                "file_exists": True,
                "preview_url": url if mime_type.startswith("image/") else None,
                "usages": [],
                "usage_count": 0,
                "search_haystack": [file_path.name, normalized, url, "unused"],
            }
        )
    results.sort(key=lambda item: item["title"])
    return results


def delete_unused_media_files():
    deleted = 0
    for asset in collect_unused_media_file_entries():
        file_path = Path(asset["storage_path"])
        if file_path.exists() and file_path.is_file():
            file_path.unlink()
            deleted += 1
    return deleted
