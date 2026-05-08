from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from shop.filtering import build_catalog_facets_payload, build_catalog_results_payload
from shop.serializers import CatalogQuerySerializer


@extend_schema(tags=["catalog"])
class CatalogResultsView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=CatalogQuerySerializer,
        responses={200: {"type": "object"}},
        summary="Catalog product results for brand/group/search context",
    )
    def post(self, request):
        serializer = CatalogQuerySerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        return Response(build_catalog_results_payload(serializer.validated_data))


@extend_schema(tags=["catalog"])
class CatalogFacetsView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=CatalogQuerySerializer,
        responses={200: {"type": "object"}},
        summary="Catalog facets for brand/group/search context",
    )
    def post(self, request):
        serializer = CatalogQuerySerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        return Response(build_catalog_facets_payload(serializer.validated_data))
