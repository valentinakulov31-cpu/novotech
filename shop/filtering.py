from decimal import Decimal, InvalidOperation

from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Case, Count, F, FloatField, IntegerField, Max, Min, Q, Value, When, Window
from django.db.models.functions import Cast, Coalesce, Greatest, RowNumber

from shop.models import Brand, Characteristic, Group, Product, ProductCharacteristic
from shop.seo import build_product_seo, resolve_city


SEARCH_FUZZY_THRESHOLD = 0.18


def parse_bool(value):
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "y", "да"}:
        return True
    if normalized in {"false", "0", "no", "n", "нет"}:
        return False
    return None


def parse_decimal(value):
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value).strip().replace(" ", "").replace(",", "."))
    except (InvalidOperation, ValueError):
        return None


def tokenize_query(query):
    return [token for token in str(query or "").split() if token.strip()]


def any_field_matches(token, fields):
    token_query = Q()
    for field in fields:
        token_query |= Q(**{f"{field}__icontains": token})
    return token_query


def token_match_query(tokens, fields, require_all=True):
    if not tokens:
        return Q()
    queries = [any_field_matches(token, fields) for token in tokens]
    if require_all:
        query = Q()
        for token_query in queries:
            query &= token_query
        return query
    query = Q()
    for token_query in queries:
        query |= token_query
    return query


def score_expression(tokens, fields):
    score = Value(0, output_field=IntegerField())
    for token in tokens:
        token_query = any_field_matches(token, fields)
        score += Case(
            When(token_query, then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
    return score


def fuzzy_similarity_expression(query, tokens, fields):
    expressions = []
    for field in fields:
        coalesced_field = Coalesce(field, Value(""))
        expressions.append(TrigramSimilarity(coalesced_field, query))
        for token in tokens:
            expressions.append(TrigramSimilarity(coalesced_field, token))
    if not expressions:
        return Value(0.0, output_field=FloatField())
    return Greatest(*expressions, Value(0.0, output_field=FloatField()))


def apply_ranked_search(queryset, query, exact_fields, fuzzy_fields=None, require_all_tokens=True, threshold=SEARCH_FUZZY_THRESHOLD):
    query = (query or "").strip()
    tokens = tokenize_query(query)
    if not tokens:
        return queryset

    fuzzy_fields = fuzzy_fields or exact_fields
    queryset = queryset.annotate(
        search_exact_score=score_expression(tokens, exact_fields),
        search_similarity=fuzzy_similarity_expression(query, tokens, fuzzy_fields),
    ).annotate(
        search_rank=Cast("search_exact_score", FloatField()) + Cast("search_similarity", FloatField())
    )
    exact_query = token_match_query(tokens, exact_fields, require_all=require_all_tokens)
    queryset = queryset.filter(exact_query | Q(search_similarity__gte=threshold))
    queryset = queryset.annotate(
        _search_row_number=Window(
            expression=RowNumber(),
            partition_by=[F("pk")],
            order_by=[F("search_rank").desc(), F("search_similarity").desc(), F("pk").asc()],
        )
    ).filter(_search_row_number=1)
    return queryset.distinct()


def _build_legacy_payload(payload):
    return {
        "context": {
            "q": payload.get("q"),
            "city_slug": payload.get("city_slug"),
            "group_id": payload.get("group_id"),
            "brand_ids": payload.get("brand_ids") or [],
        },
        "filters": {
            "brand_ids": payload.get("brand_ids") or [],
            "available": payload.get("available"),
            "price": {
                "min": payload.get("min_price"),
                "max": payload.get("max_price"),
            },
            "attributes": payload.get("attributes") or {},
        },
        "page": payload.get("page", 1),
        "page_size": payload.get("page_size", 24),
        "sort": payload.get("sort", "relevance"),
    }


def normalize_catalog_payload(payload):
    payload = payload or {}
    if "context" not in payload and "filters" not in payload:
        payload = _build_legacy_payload(payload)

    context = payload.get("context") or {}
    filters = payload.get("filters") or {}
    price = filters.get("price") or {}

    normalized = {
        "context": {
            "q": (context.get("q") or "").strip() or None,
            "city_slug": (context.get("city_slug") or "").strip() or None,
            "group_id": context.get("group_id"),
            "group_slug": (context.get("group_slug") or "").strip() or None,
            "brand_id": context.get("brand_id"),
            "brand_slug": (context.get("brand_slug") or "").strip() or None,
        },
        "filters": {
            "group_ids": filters.get("group_ids") or [],
            "group_slugs": filters.get("group_slugs") or [],
            "brand_ids": filters.get("brand_ids") or [],
            "brand_slugs": filters.get("brand_slugs") or [],
            "available": parse_bool(filters.get("available")),
            "price": {
                "min": parse_decimal(price.get("min")),
                "max": parse_decimal(price.get("max")),
            },
            "attributes": filters.get("attributes") or {},
        },
        "page": max(int(payload.get("page") or 1), 1),
        "page_size": min(max(int(payload.get("page_size") or 24), 1), 100),
        "sort": (payload.get("sort") or "relevance").strip() or "relevance",
    }

    for key in ("group_id", "brand_id"):
        value = normalized["context"][key]
        if value in ("", None):
            normalized["context"][key] = None
        else:
            try:
                normalized["context"][key] = int(value)
            except (TypeError, ValueError):
                normalized["context"][key] = None

    normalized["filters"]["group_ids"] = [int(item) for item in normalized["filters"]["group_ids"] if str(item).isdigit()]
    normalized["filters"]["brand_ids"] = [int(item) for item in normalized["filters"]["brand_ids"] if str(item).isdigit()]
    normalized["filters"]["group_slugs"] = [str(item).strip() for item in normalized["filters"]["group_slugs"] if str(item).strip()]
    normalized["filters"]["brand_slugs"] = [str(item).strip() for item in normalized["filters"]["brand_slugs"] if str(item).strip()]
    return normalized


def build_filter_payload_from_query_params(params):
    attributes = {}
    for key in params.keys():
        if key.startswith("attr."):
            slug = key[5:]
            raw_values = params.getlist(key)
            values = []
            for raw in raw_values:
                values.extend([item.strip() for item in str(raw).split(",") if item.strip()])
            attributes[slug] = values

    brand_values = params.getlist("brand_id")
    brand_ids = []
    for value in brand_values:
        brand_ids.extend([int(item) for item in str(value).split(",") if item.strip().isdigit()])

    return {
        "q": params.get("q"),
        "city_slug": params.get("city_slug"),
        "group_id": int(params.get("group_id")) if str(params.get("group_id") or "").isdigit() else None,
        "brand_ids": brand_ids,
        "available": params.get("available"),
        "min_price": params.get("min_price"),
        "max_price": params.get("max_price"),
        "attributes": attributes,
    }


def build_catalog_base_queryset(payload, queryset=None, exclude=None):
    payload = normalize_catalog_payload(payload)
    exclude = exclude or {}
    queryset = queryset or Product.objects.all()
    context = payload["context"]
    filters = payload["filters"]

    queryset = queryset.select_related("group", "brand").prefetch_related(
        "media_files",
        "gallery_items",
        "documents",
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
        tokens = tokenize_query(q)
        search_fields = [
            "sku",
            "name",
            "description",
            "characteristics_html",
            "search_tsv",
            "group__name",
            "group__slug",
            "brand__name",
            "brand__slug",
            "characteristics__value",
            "characteristics__characteristic__name",
            "characteristics__characteristic__slug",
        ]
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
        "documents_list": [
            {
                "id": item.id,
                "title": item.title,
                "url": item.url,
                "mime_type": item.mime_type,
                "sort_order": item.sort_order,
            }
            for item in product.documents.all()
        ],
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


def _serialize_brand_facets(queryset, payload):
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


def _serialize_group_facets(queryset, payload):
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


def _serialize_attribute_facets(base_queryset, payload):
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
        "groups": _serialize_group_facets(groups_queryset, payload),
        "brands": _serialize_brand_facets(brands_queryset, payload),
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
        "attributes": _serialize_attribute_facets(filtered_queryset, payload),
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
