from shop.models import Product
from shop.seo import build_group_seo, build_product_seo


def serialize_public_group_summary(group, city=None) -> dict:
    return {
        "id": group.id,
        "parent_id": group.parent_id,
        "name": group.name,
        "slug": group.slug,
        "description": group.description,
        "media": group.media,
        "seo": build_group_seo(group, city=city),
    }


def serialize_public_product_summary(product: Product, city=None, *, group_slug=None, brand_slug=None) -> dict:
    return {
        "id": product.id,
        "sku": product.sku,
        "slug": product.slug,
        "name": product.name,
        "price": float(product.price),
        "currency": product.currency,
        "description": product.description,
        "group_id": product.group_id,
        "brand_id": product.brand_id,
        "group_slug": group_slug if group_slug is not None else (product.group.slug if product.group else None),
        "brand_slug": brand_slug if brand_slug is not None else (product.brand.slug if product.brand else None),
        "media": product.media,
        "available": product.available,
        "seo": build_product_seo(product, city=city),
    }


def serialize_product_detail_payload(product: Product, city=None) -> dict:
    gallery_items = [
        {
            "id": item.id,
            "product_id": item.product_id,
            "title": item.title,
            "url": item.url,
            "mime_type": item.mime_type,
            "file_kind": item.file_kind,
            "size_bytes": item.size_bytes,
            "sort_order": item.sort_order,
        }
        for item in product.gallery_items.all().order_by("sort_order", "id")
    ]
    if product.shared_gallery_id:
        gallery_items.extend(
            {
                "id": item.id,
                "shared_gallery_id": item.gallery_id,
                "title": item.title,
                "url": item.url,
                "mime_type": item.mime_type,
                "file_kind": item.file_kind,
                "size_bytes": item.size_bytes,
                "sort_order": item.sort_order,
            }
            for item in product.shared_gallery.items.all().order_by("sort_order", "id")
        )

    return {
        **serialize_public_product_summary(product, city=city),
        "assortment_html": product.assortment_html,
        "characteristics_html": product.characteristics_html,
        "media_list": [
            {
                "id": item.id,
                "url": item.url,
                "mime_type": item.mime_type,
                "media_kind": item.media_kind,
                "size_bytes": item.size_bytes,
                "variants": item.variants,
                "is_primary": item.is_primary,
                "sort_order": item.sort_order,
                "alt_text": item.alt_text,
            }
            for item in product.media_files.all().order_by("-is_primary", "sort_order", "id")
        ],
        "gallery": gallery_items,
        "certificates_list": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "title": item.title,
                "url": item.url,
                "mime_type": item.mime_type,
                "size_bytes": item.size_bytes,
                "sort_order": item.sort_order,
            }
            for item in product.certificates.all().order_by("sort_order", "id")
        ],
        "attributes": [
            {
                "id": item.characteristic.id,
                "name": item.characteristic.name,
                "unit": item.characteristic.unit,
                "value": item.value,
            }
            for item in product.characteristics.select_related("characteristic").all()
        ],
    }
