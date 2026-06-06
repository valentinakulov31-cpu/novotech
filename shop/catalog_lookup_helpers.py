from django.db.models import Q
from django.shortcuts import get_object_or_404

from shop.models import Brand, Group, Product


def get_product_by_identifier(product_identifier):
    lookup = Q(slug=product_identifier)
    if str(product_identifier).isdigit():
        lookup |= Q(id=int(product_identifier))
    queryset = Product.objects.select_related("group", "brand", "shared_gallery").prefetch_related(
        "media_files",
        "gallery_items",
        "certificates",
        "characteristics__characteristic",
        "shared_gallery__items",
    )
    return get_object_or_404(queryset, lookup)


def get_group_by_identifier(group_identifier):
    if str(group_identifier).isdigit():
        return get_object_or_404(Group, id=int(group_identifier))
    return get_object_or_404(Group, slug=group_identifier)


def get_brand_by_identifier(brand_identifier):
    if str(brand_identifier).isdigit():
        return get_object_or_404(Brand, id=int(brand_identifier))
    return get_object_or_404(Brand, slug=brand_identifier)
