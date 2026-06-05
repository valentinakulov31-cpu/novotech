from django.db.models import FloatField
from django.db.models.functions import Cast

from shop.filtering_catalog_payload import normalize_catalog_payload
from shop.filtering_search import apply_ranked_search, parse_decimal, tokenize_query
from shop.models import Product, ProductCharacteristic


def build_catalog_base_queryset(payload, queryset=None, exclude=None):
    payload = normalize_catalog_payload(payload)
    exclude = exclude or {}
    queryset = queryset or Product.objects.all()
    context = payload["context"]
    filters = payload["filters"]

    queryset = queryset.select_related("group", "brand").prefetch_related(
        "media_files",
        "gallery_items",
        "certificates",
        "characteristics__characteristic",
    )

    group_ids = []
    if context["group_id"] and not exclude.get("base_group"):
        group_ids.append(context["group_id"])
    if context["group_slug"] and not exclude.get("base_group"):
        queryset = queryset.filter(group__slug=context["group_slug"])
    if filters["group_ids"] and not exclude.get("base_group"):
        group_ids.extend(filters["group_ids"])
    if filters["group_slugs"] and not exclude.get("base_group"):
        queryset = queryset.filter(group__slug__in=filters["group_slugs"])
    if group_ids:
        queryset = queryset.filter(group_id__in=group_ids)

    brand_ids = list(filters["brand_ids"])
    if context["brand_id"] and not exclude.get("base_brand"):
        brand_ids.append(context["brand_id"])
    if context["brand_slug"] and not exclude.get("base_brand"):
        queryset = queryset.filter(brand__slug=context["brand_slug"])
    if filters["brand_slugs"] and not exclude.get("base_brand"):
        queryset = queryset.filter(brand__slug__in=filters["brand_slugs"])
    if brand_ids:
        queryset = queryset.filter(brand_id__in=brand_ids)

    q = context["q"]
    if q:
        tokenize_query(q)
        search_fields = ["search_index"]
        queryset = apply_ranked_search(
            queryset,
            q,
            exact_fields=search_fields,
            fuzzy_fields=search_fields,
            require_all_tokens=True,
        )

    return queryset.distinct()


def _attribute_filter_product_ids(slug, rule):
    queryset = ProductCharacteristic.objects.filter(characteristic__slug=slug).exclude(value__isnull=True).exclude(value="")
    if isinstance(rule, dict):
        min_value = parse_decimal(rule.get("min"))
        max_value = parse_decimal(rule.get("max"))
        queryset = queryset.filter(value__regex=r"^-?\d+([.,]\d+)?$")
        queryset = queryset.annotate(value_num=Cast("value", FloatField()))
        if min_value is not None:
            queryset = queryset.filter(value_num__gte=float(min_value))
        if max_value is not None:
            queryset = queryset.filter(value_num__lte=float(max_value))
    else:
        values = [str(value).strip() for value in rule if str(value).strip()]
        if not values:
            return Product.objects.none().values_list("id", flat=True)
        queryset = queryset.filter(value__in=values)
    return queryset.values_list("product_id", flat=True)


def apply_catalog_filters(queryset, payload: dict, exclude=None):
    payload = normalize_catalog_payload(payload)
    exclude = exclude or {}
    queryset = build_catalog_base_queryset(payload, queryset=queryset, exclude=exclude)
    filters = payload["filters"]

    if not exclude.get("available") and filters["available"] is not None:
        queryset = queryset.filter(available=filters["available"])

    if not exclude.get("price"):
        min_price = filters["price"]["min"]
        max_price = filters["price"]["max"]
        if min_price is not None:
            queryset = queryset.filter(price__gte=min_price)
        if max_price is not None:
            queryset = queryset.filter(price__lte=max_price)

    if not exclude.get("attributes"):
        for slug, rule in (filters["attributes"] or {}).items():
            if exclude.get("attribute_slug") == slug:
                continue
            queryset = queryset.filter(id__in=_attribute_filter_product_ids(slug, rule))

    return queryset.distinct()


def apply_catalog_sort(queryset, payload):
    payload = normalize_catalog_payload(payload)
    sort = payload["sort"]
    q = payload["context"]["q"]

    if sort == "price_asc":
        return queryset.order_by("price", "name", "id")
    if sort == "price_desc":
        return queryset.order_by("-price", "name", "id")
    if sort == "name_desc":
        return queryset.order_by("-name", "id")
    if sort == "popular":
        return queryset.order_by("?")
    if q:
        return queryset.order_by("-search_rank", "name", "id")
    return queryset.order_by("name", "id")
