from shop.filtering_catalog_payload import normalize_catalog_payload
from shop.filtering_catalog_query import apply_catalog_filters, apply_catalog_sort
from shop.models import Product
from shop.product_presenters import serialize_public_product_summary
from shop.seo import resolve_city


def serialize_product_card(product: Product, city=None) -> dict:
    return serialize_public_product_summary(product, city=city)


def build_catalog_results_payload(payload):
    payload = normalize_catalog_payload(payload)
    queryset = apply_catalog_filters(Product.objects.all(), payload)
    total = queryset.count()
    ordered = apply_catalog_sort(queryset, payload)
    start = (payload["page"] - 1) * payload["page_size"]
    end = start + payload["page_size"]
    page_items = list(ordered[start:end])
    city = resolve_city(city_slug=payload["context"].get("city_slug"))
    return {
        "context": payload["context"],
        "pagination": {
            "count": total,
            "page": payload["page"],
            "page_size": payload["page_size"],
            "pages": (total + payload["page_size"] - 1) // payload["page_size"] if payload["page_size"] else 1,
        },
        "sort": payload["sort"],
        "results": [serialize_product_card(product, city=city) for product in page_items],
    }
