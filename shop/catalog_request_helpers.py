from shop.filtering import (
    apply_catalog_filters,
    build_catalog_facets_payload,
    build_catalog_results_payload,
    build_facets,
    build_filter_payload_from_query_params,
)
from shop.models import Product
from shop.serializers import CatalogQuerySerializer
from shop.view_transport_helpers import validate_request_data


def build_filter_facets_from_query_params(params, *, group_id=None):
    payload = build_filter_payload_from_query_params(params)
    if group_id is not None:
        payload["group_id"] = group_id
    queryset = apply_catalog_filters(Product.objects.select_related("group", "brand"), payload)
    facets = build_facets(queryset)
    facets["scope"] = {"group_id": group_id if group_id is not None else payload.get("group_id")}
    facets["count"] = queryset.count()
    return facets


def build_catalog_results_from_request(request):
    payload = validate_request_data(CatalogQuerySerializer, request)
    return build_catalog_results_payload(payload)


def build_catalog_facets_from_request(request):
    payload = validate_request_data(CatalogQuerySerializer, request)
    return build_catalog_facets_payload(payload)
