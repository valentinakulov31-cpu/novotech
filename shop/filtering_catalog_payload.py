from shop.filtering_search import parse_bool, parse_decimal


def _build_legacy_payload(payload):
    return {
        "context": {
            "q": payload.get("q"),
            "city_slug": payload.get("city_slug"),
            "group_id": payload.get("group_id"),
            "brand_ids": payload.get("brand_ids") or [],
        },
        "filters": {
            "brand_ids": payload.get("brand_ids") or [],
            "available": payload.get("available"),
            "price": {
                "min": payload.get("min_price"),
                "max": payload.get("max_price"),
            },
            "attributes": payload.get("attributes") or {},
        },
        "page": payload.get("page", 1),
        "page_size": payload.get("page_size", 24),
        "sort": payload.get("sort", "relevance"),
    }


def normalize_catalog_payload(payload):
    payload = payload or {}
    if "context" not in payload and "filters" not in payload:
        payload = _build_legacy_payload(payload)

    context = payload.get("context") or {}
    filters = payload.get("filters") or {}
    price = filters.get("price") or {}

    normalized = {
        "context": {
            "q": (context.get("q") or "").strip() or None,
            "city_slug": (context.get("city_slug") or "").strip() or None,
            "group_id": context.get("group_id"),
            "group_slug": (context.get("group_slug") or "").strip() or None,
            "brand_id": context.get("brand_id"),
            "brand_slug": (context.get("brand_slug") or "").strip() or None,
        },
        "filters": {
            "group_ids": filters.get("group_ids") or [],
            "group_slugs": filters.get("group_slugs") or [],
            "brand_ids": filters.get("brand_ids") or [],
            "brand_slugs": filters.get("brand_slugs") or [],
            "available": parse_bool(filters.get("available")),
            "price": {
                "min": parse_decimal(price.get("min")),
                "max": parse_decimal(price.get("max")),
            },
            "attributes": filters.get("attributes") or {},
        },
        "page": max(int(payload.get("page") or 1), 1),
        "page_size": min(max(int(payload.get("page_size") or 24), 1), 100),
        "sort": (payload.get("sort") or "relevance").strip() or "relevance",
    }

    for key in ("group_id", "brand_id"):
        value = normalized["context"][key]
        if value in ("", None):
            normalized["context"][key] = None
        else:
            try:
                normalized["context"][key] = int(value)
            except (TypeError, ValueError):
                normalized["context"][key] = None

    normalized["filters"]["group_ids"] = [int(item) for item in normalized["filters"]["group_ids"] if str(item).isdigit()]
    normalized["filters"]["brand_ids"] = [int(item) for item in normalized["filters"]["brand_ids"] if str(item).isdigit()]
    normalized["filters"]["group_slugs"] = [str(item).strip() for item in normalized["filters"]["group_slugs"] if str(item).strip()]
    normalized["filters"]["brand_slugs"] = [str(item).strip() for item in normalized["filters"]["brand_slugs"] if str(item).strip()]
    return normalized


def build_filter_payload_from_query_params(params):
    attributes = {}
    for key in params.keys():
        if key.startswith("attr."):
            slug = key[5:]
            raw_values = params.getlist(key)
            values = []
            for raw in raw_values:
                values.extend([item.strip() for item in str(raw).split(",") if item.strip()])
            attributes[slug] = values

    brand_values = params.getlist("brand_id")
    brand_ids = []
    for value in brand_values:
        brand_ids.extend([int(item) for item in str(value).split(",") if item.strip().isdigit()])

    return {
        "q": params.get("q"),
        "city_slug": params.get("city_slug"),
        "group_id": int(params.get("group_id")) if str(params.get("group_id") or "").isdigit() else None,
        "brand_ids": brand_ids,
        "available": params.get("available"),
        "min_price": params.get("min_price"),
        "max_price": params.get("max_price"),
        "attributes": attributes,
    }
