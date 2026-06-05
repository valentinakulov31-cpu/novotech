from shop.models import Product
from shop.product_presenters import serialize_public_group_summary, serialize_public_product_summary
from shop.seo import build_group_seo


def build_group_tree(groups, city=None):
    id_to_node = {
        group.id: {
            "id": group.id,
            "parent_id": group.parent_id,
            "name": group.name,
            "slug": group.slug,
            "description": group.description,
            "media": group.media,
            "seo": build_group_seo(group, city=city),
            "children": [],
        }
        for group in groups
    }

    roots = []
    for group in groups:
        node = id_to_node[group.id]
        if group.parent_id and group.parent_id in id_to_node:
            id_to_node[group.parent_id]["children"].append(node)
        else:
            roots.append(node)

    return roots


def build_group_with_products_payload(group, *, city=None):
    products = Product.objects.filter(group=group)
    products_list = [
        serialize_public_product_summary(product, city=city, group_slug=group.slug)
        for product in products
    ]
    return {
        "category": serialize_public_group_summary(group, city=city),
        "products": products_list,
    }


def build_brand_grouped_products_payload(brand, *, city=None):
    products = Product.objects.filter(brand=brand).select_related("group")
    grouped = {}
    for product in products:
        if product.group:
            category_key = product.group.slug
            if category_key not in grouped:
                grouped[category_key] = {
                    **serialize_public_group_summary(product.group, city=city),
                    "products": [],
                }
        else:
            category_key = "uncategorized"
            if category_key not in grouped:
                grouped[category_key] = {
                    "id": None,
                    "slug": None,
                    "name": None,
                    "parent_id": None,
                    "products": [],
                }

        grouped[category_key]["products"].append(
            serialize_public_product_summary(product, city=city, brand_slug=brand.slug)
        )

    return {
        "brand": {
            "id": brand.id,
            "name": brand.name,
            "slug": brand.slug,
            "media": brand.media,
        },
        "categories": list(grouped.values()),
    }
