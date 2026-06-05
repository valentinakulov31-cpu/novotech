from shop.filtering_catalog_payload import normalize_catalog_payload
from shop.filtering_catalog_query import apply_catalog_filters, apply_catalog_sort
from shop.models import Product
from shop.seo import build_product_seo, resolve_city


def serialize_product_card(product: Product, city=None) -> dict:
    media_list = [
        {
            "id": item.id,
            "url": item.url,
            "mime_type": item.mime_type,
            "media_kind": item.media_kind,
            "is_primary": item.is_primary,
            "sort_order": item.sort_order,
            "alt_text": item.alt_text,
        }
        for item in product.media_files.all()
    ]
    gallery = [
        {
            "id": item.id,
            "title": item.title,
            "url": item.url,
            "mime_type": item.mime_type,
            "file_kind": item.file_kind,
            "sort_order": item.sort_order,
        }
        for item in product.gallery_items.all()
    ]
    return {
        "id": product.id,
        "sku": product.sku,
        "slug": product.slug,
        "name": product.name,
        "price": float(product.price),
        "currency": product.currency,
        "description": product.description,
        "assortment_html": product.assortment_html,
        "characteristics_html": product.characteristics_html,
        "group_id": product.group_id,
        "brand_id": product.brand_id,
        "group_slug": product.group.slug if product.group else None,
        "brand_slug": product.brand.slug if product.brand else None,
        "media": product.media,
        "available": product.available,
        "seo": build_product_seo(product, city=city),
        "media_list": media_list,
        "gallery": gallery,
        "certificates_list": [
            {
                "id": item.id,
                "title": item.title,
                "url": item.url,
                "mime_type": item.mime_type,
                "sort_order": item.sort_order,
            }
            for item in product.certificates.all()
        ],
    }


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
