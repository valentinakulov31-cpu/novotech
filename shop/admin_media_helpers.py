import mimetypes
from pathlib import Path
from urllib.parse import urlparse

from django.conf import settings
from django.urls import reverse


def extract_media_url(value):
    if not value:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("url", "src", "path"):
            if value.get(key):
                return value[key]
        return None
    if isinstance(value, list):
        for item in value:
            url = extract_media_url(item)
            if url:
                return url
    return None


def iter_json_media_items(value):
    if value in (None, "", []):
        return
    items = value if isinstance(value, list) else [value]
    for item in items:
        if isinstance(item, str):
            url = item.strip()
            if url:
                yield {"url": url, "storage_path": None, "title": None}
            continue
        if isinstance(item, dict):
            url = item.get("url") or item.get("src") or item.get("path")
            storage_path = item.get("storage_path")
            title = item.get("title") or item.get("name") or item.get("alt")
            if url or storage_path:
                yield {"url": url, "storage_path": storage_path, "title": title}


def guess_media_mime_type(url: str | None, fallback: str | None = None) -> str:
    if fallback:
        return fallback
    guessed = mimetypes.guess_type(urlparse(str(url or "")).path)[0]
    return guessed or "application/octet-stream"


def is_local_media_url(url: str | None) -> bool:
    if not url:
        return False
    parsed = urlparse(str(url))
    return not parsed.scheme and str(url).startswith(str(settings.MEDIA_URL))


def resolve_media_storage_path(url: str | None = None, storage_path: str | None = None) -> str | None:
    if storage_path:
        path = Path(storage_path)
        if not path.is_absolute():
            path = Path(settings.MEDIA_ROOT) / path
        return str(path)
    if is_local_media_url(url):
        relative = str(url)[len(str(settings.MEDIA_URL)):].lstrip("/")
        return str(Path(settings.MEDIA_ROOT) / Path(relative))
    return None


def build_media_asset_key(url: str | None = None, storage_path: str | None = None) -> str | None:
    resolved_storage_path = resolve_media_storage_path(url=url, storage_path=storage_path)
    if resolved_storage_path:
        return f"path::{resolved_storage_path}"
    if url:
        return f"url::{url}"
    return None


def build_admin_change_url(instance) -> str | None:
    try:
        return reverse(f"admin:{instance._meta.app_label}_{instance._meta.model_name}_change", args=[instance.pk])
    except Exception:
        return None


def media_item_matches(value, asset_url: str | None, asset_storage_path: str | None) -> bool:
    if isinstance(value, str):
        return bool(asset_url and value == asset_url)
    if isinstance(value, dict):
        url = value.get("url") or value.get("src") or value.get("path")
        storage_path = value.get("storage_path")
        if asset_storage_path and storage_path:
            return resolve_media_storage_path(storage_path=storage_path) == resolve_media_storage_path(storage_path=asset_storage_path)
        return bool(asset_url and url == asset_url)
    return False


def strip_asset_from_json_media(value, asset_url: str | None, asset_storage_path: str | None):
    if not isinstance(value, list):
        return value
    return [item for item in value if not media_item_matches(item, asset_url, asset_storage_path)]
