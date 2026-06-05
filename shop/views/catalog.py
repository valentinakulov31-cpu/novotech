from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from shop.catalog_request_helpers import build_catalog_facets_from_request, build_catalog_results_from_request
from shop.serializers import CatalogQuerySerializer


@extend_schema(tags=["catalog"])
class CatalogResultsView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        request=CatalogQuerySerializer,
        responses={200: {"type": "object"}},
        summary="Catalog product results for brand/group/search context",
    )
    def post(self, request):
        return Response(build_catalog_results_from_request(request))


@extend_schema(tags=["catalog"])
class CatalogFacetsView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        request=CatalogQuerySerializer,
        responses={200: {"type": "object"}},
        summary="Catalog facets for brand/group/search context",
    )
    def post(self, request):
        return Response(build_catalog_facets_from_request(request))
