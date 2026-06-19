from shop.filtering import apply_ranked_search, tokenize_query, tokenize_query_groups
from shop.model_utils import normalize_search_token
from shop.models import Brand, Characteristic, Group, Product
from shop.search_presenters import (
    serialize_brand,
    serialize_characteristic,
    serialize_group,
    serialize_product,
)
from shop.seo import resolve_city


def _serialize_search_debug_items(queryset):
    items = []
    for item in queryset:
        items.append(
            {
                "id": item.id,
                "name": getattr(item, "name", ""),
                "slug": getattr(item, "slug", ""),
                "search_rank": float(getattr(item, "search_rank", 0.0) or 0.0),
                "search_similarity": float(getattr(item, "search_similarity", 0.0) or 0.0),
                "search_exact_score": int(getattr(item, "search_exact_score", 0) or 0),
            }
        )
    return items


def _serialize_token_groups_for_debug(token_groups):
    groups = []
    for variants in token_groups:
        filtered = []
        for variant in variants:
            raw_variant = str(variant or "").strip()
            if len(raw_variant) >= 2 and any(not char.isalnum() for char in raw_variant):
                filtered.append(variant)
                continue
            normalized = normalize_search_token(variant)
            if len(normalized) < 2 and normalized.isalpha():
                continue
            filtered.append(variant)
        if filtered:
            groups.append(filtered)
    return groups


def _sort_products_for_navigation(products, top_group=None, top_brand=None):
    def sort_key(product):
        return (
            0 if top_brand and product.brand_id == top_brand.id else 1,
            0 if top_group and product.group_id == top_group.id else 1,
            -(float(getattr(product, "search_rank", 0.0) or 0.0)),
            -(float(getattr(product, "search_similarity", 0.0) or 0.0)),
            getattr(product, "name", ""),
            product.id,
        )

    return sorted(products, key=sort_key)


def build_global_search_payload(query: str, city_slug: str | None = None, debug: bool = False) -> dict:
    query = (query or "").strip()
    city = resolve_city(city_slug=city_slug)
    tokens = tokenize_query(query)
    token_groups = tokenize_query_groups(query)
    if not tokens:
        payload = {
            "query": query,
            "tokens": [],
            "navigation": {"group": None, "brand": None, "mode": None},
            "results": {
                "products": [],
                "groups": [],
                "brands": [],
                "characteristics": [],
            },
        }
        if debug:
            payload["debug"] = {"token_groups": []}
        return payload

    product_fields = ["search_index"]
    group_fields = ["search_index"]
    brand_fields = ["search_index"]
    characteristic_fields = ["search_index"]

    groups = (
        apply_ranked_search(
            Group.objects.all(),
            query,
            exact_fields=group_fields,
            fuzzy_fields=group_fields,
            require_all_tokens=False,
        )
        .order_by("-search_rank", "-search_similarity", "name")[:10]
    )

    brands = (
        apply_ranked_search(
            Brand.objects.all(),
            query,
            exact_fields=brand_fields,
            fuzzy_fields=brand_fields,
            require_all_tokens=False,
        )
        .order_by("-search_rank", "-search_similarity", "name")[:10]
    )
    characteristics = (
        apply_ranked_search(
            Characteristic.objects.select_related("group"),
            query,
            exact_fields=characteristic_fields,
            fuzzy_fields=characteristic_fields,
            require_all_tokens=False,
        )
        .order_by("-search_rank", "-search_similarity", "name")[:15]
    )

    top_group = groups[0] if groups else None
    top_brand = brands[0] if brands else None

    mode = None
    if top_group and top_brand:
        mode = "group_brand"
    elif top_group:
        mode = "group"
    elif top_brand:
        mode = "brand"

    products = list(
        apply_ranked_search(
            Product.objects.filter(is_hidden=False).select_related("group", "brand"),
            query,
            exact_fields=product_fields,
            fuzzy_fields=product_fields,
            require_all_tokens=True,
        )
        .distinct()
        .order_by("-search_rank", "-search_similarity", "name")[:30]
    )
    products = _sort_products_for_navigation(products, top_group=top_group, top_brand=top_brand)

    payload = {
        "query": query,
        "tokens": tokens,
        "navigation": {
            "mode": mode,
            "group": serialize_group(top_group, city=city) if top_group else None,
            "brand": serialize_brand(top_brand) if top_brand else None,
        },
        "results": {
            "products": [serialize_product(product, city=city) for product in products],
            "groups": [serialize_group(group, city=city) for group in groups],
            "brands": [serialize_brand(brand) for brand in brands],
            "characteristics": [serialize_characteristic(characteristic, city=city) for characteristic in characteristics],
        },
    }
    if debug:
        payload["debug"] = {
            "token_groups": _serialize_token_groups_for_debug(token_groups),
            "products": _serialize_search_debug_items(products[:10]),
            "groups": _serialize_search_debug_items(groups[:10]),
            "brands": _serialize_search_debug_items(brands[:10]),
            "characteristics": _serialize_search_debug_items(characteristics[:10]),
        }
    return payload
