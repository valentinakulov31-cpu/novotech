from django.db.models import Count, FloatField, Max, Min, Q
from django.db.models.functions import Cast

from shop.filtering_catalog import apply_catalog_filters
from shop.filtering_search import parse_decimal
from shop.models import Brand, Characteristic, Group, Product, ProductCharacteristic


def serialize_brand_facets(queryset, payload):
    product_ids = queryset.values_list("id", flat=True)
    selected = set(payload["filters"]["brand_slugs"])
    if payload["context"]["brand_slug"]:
        selected.add(payload["context"]["brand_slug"])

    rows = (
        Brand.objects.filter(products__id__in=product_ids)
        .annotate(product_count=Count("products", filter=Q(products__id__in=product_ids), distinct=True))
        .order_by("name")
        .values("id", "name", "slug", "product_count")
        .distinct()
    )
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "slug": row["slug"],
            "count": row["product_count"],
            "selected": row["slug"] in selected,
        }
        for row in rows
    ]


def serialize_group_facets(queryset, payload):
    product_ids = queryset.values_list("id", flat=True)
    selected = set(payload["filters"]["group_slugs"])
    if payload["context"]["group_slug"]:
        selected.add(payload["context"]["group_slug"])

    rows = (
        Group.objects.filter(products__id__in=product_ids)
        .annotate(product_count=Count("products", filter=Q(products__id__in=product_ids), distinct=True))
        .order_by("name")
        .values("id", "name", "slug", "product_count")
        .distinct()
    )
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "slug": row["slug"],
            "count": row["product_count"],
            "selected": row["slug"] in selected,
        }
        for row in rows
    ]


def serialize_attribute_facets(base_queryset, payload):
    base_product_ids = list(base_queryset.values_list("id", flat=True))
    characteristics = (
        Characteristic.objects.filter(is_filterable=True, productcharacteristic__product_id__in=base_product_ids)
        .distinct()
        .order_by("name")
    )
    attribute_facets = []
    selected_attributes = payload["filters"]["attributes"]

    for characteristic in characteristics:
        queryset = apply_catalog_filters(
            Product.objects.all(),
            payload,
            exclude={"attributes": True, "attribute_slug": characteristic.slug},
        )
        product_ids = list(queryset.values_list("id", flat=True))
        facet = {
            "id": characteristic.id,
            "name": characteristic.name,
            "slug": characteristic.slug,
            "type": characteristic.data_type,
            "mode": "range" if characteristic.data_type == "number" else "multi_select",
            "unit": characteristic.unit,
            "selected": selected_attributes.get(characteristic.slug),
        }

        values_queryset = ProductCharacteristic.objects.filter(
            product_id__in=product_ids,
            characteristic=characteristic,
        ).exclude(value__isnull=True).exclude(value="")

        if characteristic.data_type == "number":
            numeric_values = (
                values_queryset.filter(value__regex=r"^-?\d+([.,]\d+)?$")
                .annotate(value_num=Cast("value", FloatField()))
                .aggregate(min_value=Min("value_num"), max_value=Max("value_num"))
            )
            selected_range = selected_attributes.get(characteristic.slug) if isinstance(selected_attributes.get(characteristic.slug), dict) else {}
            facet["range"] = {
                "min": float(numeric_values["min_value"]) if numeric_values["min_value"] is not None else None,
                "max": float(numeric_values["max_value"]) if numeric_values["max_value"] is not None else None,
                "selected_min": float(parse_decimal(selected_range.get("min"))) if parse_decimal(selected_range.get("min")) is not None else None,
                "selected_max": float(parse_decimal(selected_range.get("max"))) if parse_decimal(selected_range.get("max")) is not None else None,
            }
        else:
            selected_values = selected_attributes.get(characteristic.slug)
            if not isinstance(selected_values, list):
                selected_values = []
            facet["values"] = [
                {
                    "value": row["value"],
                    "count": row["count"],
                    "selected": row["value"] in selected_values,
                }
                for row in values_queryset.values("value").annotate(count=Count("product_id", distinct=True)).order_by("value")
            ]

        attribute_facets.append(facet)

    return attribute_facets
