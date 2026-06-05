from shop.admin_media_asset_registry import register_media_asset
from shop.admin_media_sources import iter_media_library_source_entries


def collect_media_library_assets(search_query: str = "", usage_filter: str = "") -> list[dict]:
    asset_map: dict[str, dict] = {}
    for entry in iter_media_library_source_entries():
        register_media_asset(asset_map, **entry)

    assets = list(asset_map.values())
    query = search_query.strip().lower()
    if query:
        assets = [
            asset for asset in assets
            if query in " ".join(str(part).lower() for part in asset["search_haystack"] if part)
        ]
    if usage_filter:
        assets = [
            asset for asset in assets
            if any(usage.get("source_label") == usage_filter for usage in asset["usages"])
        ]

    for asset in assets:
        asset["usage_count"] = len(asset["usages"])

    assets.sort(key=lambda item: (item["title"] or "", item["url"] or item["storage_path"] or ""))
    return assets
