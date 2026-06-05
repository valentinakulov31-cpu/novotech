from shop.filtering import apply_ranked_search, tokenize_query
from shop.models import Brand, Characteristic, Group, Product
from shop.search_presenters import (
    serialize_brand,
    serialize_characteristic,
    serialize_group,
    serialize_product,
)
from shop.seo import resolve_city


def build_global_search_payload(query: str, city_slug: str | None = None) -> dict:
    query = (query or "").strip()
    city = resolve_city(city_slug=city_slug)
    tokens = tokenize_query(query)
    if not tokens:
        return {
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

    product_fields = ["search_index"]
    group_fields = ["search_index"]
    brand_fields = ["search_index"]
    characteristic_fields = ["search_index"]

    products = (
        apply_ranked_search(
            Product.objects.select_related("group", "brand"),
            query,
            exact_fields=product_fields,
            fuzzy_fields=product_fields,
            require_all_tokens=True,
        )
        .distinct()
        .order_by("-search_rank", "-search_similarity", "name")[:30]
    )

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

    return {
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
