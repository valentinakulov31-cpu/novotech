from pathlib import Path
from urllib.parse import urlparse

from shop.admin_media_helpers import build_admin_change_url, build_media_asset_key, guess_media_mime_type, resolve_media_storage_path
from shop.file_utils import infer_file_kind


def register_media_asset(
    asset_map: dict[str, dict],
    *,
    url,
    storage_path=None,
    title=None,
    mime_type=None,
    size_bytes=None,
    usage_label=None,
    source_obj=None,
    kind=None,
):
    asset_key = build_media_asset_key(url=url, storage_path=storage_path)
    if not asset_key:
        return

    resolved_storage_path = resolve_media_storage_path(url=url, storage_path=storage_path)
    is_local = bool(resolved_storage_path)
    file_exists = bool(is_local and Path(resolved_storage_path).exists())
    asset = asset_map.get(asset_key)
    if asset is None:
        asset = {
            "asset_key": asset_key,
            "url": url,
            "storage_path": resolved_storage_path,
            "title": title or Path(urlparse(str(url or "")).path).name or Path(str(resolved_storage_path or "")).name,
            "mime_type": guess_media_mime_type(url, mime_type),
            "size_bytes": size_bytes,
            "kind": kind or infer_file_kind(guess_media_mime_type(url, mime_type)),
            "is_local": is_local,
            "file_exists": file_exists,
            "preview_url": url if (guess_media_mime_type(url, mime_type) or "").startswith("image/") else None,
            "usages": [],
            "search_haystack": [],
        }
        asset_map[asset_key] = asset
    else:
        if not asset.get("url") and url:
            asset["url"] = url
        if not asset.get("storage_path") and resolved_storage_path:
            asset["storage_path"] = resolved_storage_path
        if not asset.get("title") and title:
            asset["title"] = title
        if not asset.get("mime_type") and mime_type:
            asset["mime_type"] = mime_type
        if not asset.get("size_bytes") and size_bytes:
            asset["size_bytes"] = size_bytes
        if not asset.get("kind") and kind:
            asset["kind"] = kind

    usage_entry = {"source_label": usage_label}
    if source_obj is not None:
        usage_entry["owner_label"] = str(source_obj)
        usage_entry["owner_admin_url"] = build_admin_change_url(source_obj)
        asset["search_haystack"].extend(
            [
                source_obj._meta.verbose_name,
                source_obj._meta.model_name,
                str(source_obj),
            ]
        )

    if usage_entry not in asset["usages"]:
        asset["usages"].append(usage_entry)

    asset["search_haystack"].extend(filter(None, [usage_label, title, url, resolved_storage_path]))
