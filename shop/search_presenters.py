from shop.models import Brand, Characteristic, Group, Product
from shop.seo import build_group_seo, build_product_seo


def serialize_brand(brand: Brand) -> dict:
    return {
        "id": brand.id,
        "name": brand.name,
        "slug": brand.slug,
        "media": brand.media,
        "url": f"/brands/{brand.slug}",
    }


def serialize_group(group: Group, city=None) -> dict:
    return {
        "id": group.id,
        "parent_id": group.parent_id,
        "name": group.name,
        "slug": group.slug,
        "description": group.description,
        "media": group.media,
        "seo": build_group_seo(group, city=city),
        "url": f"/groups/{group.slug}",
    }


def serialize_product(product: Product, city=None) -> dict:
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
        "media": product.media,
        "available": product.available,
        "seo": build_product_seo(product, city=city),
        "group": serialize_group(product.group, city=city) if product.group else None,
        "brand": serialize_brand(product.brand) if product.brand else None,
        "url": f"/products/{product.slug}",
    }


def serialize_characteristic(characteristic: Characteristic, city=None) -> dict:
    return {
        "id": characteristic.id,
        "group_id": characteristic.group_id,
        "name": characteristic.name,
        "slug": characteristic.slug,
        "data_type": characteristic.data_type,
        "unit": characteristic.unit,
        "is_filterable": characteristic.is_filterable,
        "is_searchable": characteristic.is_searchable,
        "group": serialize_group(characteristic.group, city=city),
    }
