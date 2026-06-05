from django.db.models import Count, Max, Min, Q

from shop.filtering_catalog import apply_catalog_filters, normalize_catalog_payload
from shop.filtering_facet_serializers import (
    serialize_attribute_facets,
    serialize_brand_facets,
    serialize_group_facets,
)
from shop.filtering_search import parse_decimal
from shop.models import Brand, Characteristic, Product, ProductCharacteristic


def build_catalog_facets_payload(payload):
    payload = normalize_catalog_payload(payload)
    filtered_queryset = apply_catalog_filters(Product.objects.all(), payload)
    total = filtered_queryset.count()

    brands_queryset = apply_catalog_filters(Product.objects.all(), payload, exclude={"base_brand": True})
    groups_queryset = apply_catalog_filters(Product.objects.all(), payload, exclude={"base_group": True})

    price_values = filtered_queryset.aggregate(min_price=Min("price"), max_price=Max("price"))
    price_filters = payload["filters"]["price"]

    return {
        "context": payload["context"],
        "summary": {
            "total_products": total,
        },
        "groups": serialize_group_facets(groups_queryset, payload),
        "brands": serialize_brand_facets(brands_queryset, payload),
        "availability": {
            "in_stock_count": filtered_queryset.filter(available=True).count(),
            "selected": payload["filters"]["available"],
        },
        "price": {
            "min": float(price_values["min_price"]) if price_values["min_price"] is not None else None,
            "max": float(price_values["max_price"]) if price_values["max_price"] is not None else None,
            "selected_min": float(price_filters["min"]) if price_filters["min"] is not None else None,
            "selected_max": float(price_filters["max"]) if price_filters["max"] is not None else None,
        },
        "attributes": serialize_attribute_facets(filtered_queryset, payload),
    }


def build_facets(base_queryset):
    product_ids = base_queryset.values_list("id", flat=True)

    brands = list(
        Brand.objects.filter(products__id__in=product_ids)
        .annotate(product_count=Count("products", filter=Q(products__id__in=product_ids), distinct=True))
        .order_by("name")
        .values("id", "name", "slug", "product_count")
        .distinct()
    )

    price_range = base_queryset.aggregate(min_price=Min("price"), max_price=Max("price"))
    price = {
        "min": float(price_range["min_price"]) if price_range["min_price"] is not None else None,
        "max": float(price_range["max_price"]) if price_range["max_price"] is not None else None,
    }

    attributes = []
    characteristics = Characteristic.objects.filter(is_filterable=True, productcharacteristic__product_id__in=product_ids).distinct()
    for characteristic in characteristics.order_by("name"):
        value_rows = list(
            ProductCharacteristic.objects.filter(
                product_id__in=product_ids,
                characteristic=characteristic,
            )
            .exclude(value__isnull=True)
            .exclude(value="")
            .values("value")
            .annotate(count=Count("product_id", distinct=True))
            .order_by("value")
        )

        facet = {
            "id": characteristic.id,
            "name": characteristic.name,
            "slug": characteristic.slug,
            "data_type": characteristic.data_type,
            "unit": characteristic.unit,
            "is_filterable": characteristic.is_filterable,
            "is_searchable": characteristic.is_searchable,
            "values": [{"value": row["value"], "count": row["count"]} for row in value_rows],
        }

        if characteristic.data_type == "number" and value_rows:
            numeric_values = [parse_decimal(row["value"]) for row in value_rows]
            numeric_values = [value for value in numeric_values if value is not None]
            facet["range"] = {
                "min": float(min(numeric_values)) if numeric_values else None,
                "max": float(max(numeric_values)) if numeric_values else None,
            }

        attributes.append(facet)

    return {
        "brands": brands,
        "price": price,
        "attributes": attributes,
    }
