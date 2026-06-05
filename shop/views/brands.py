"""
Brand views
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, CreateAPIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from django.db.models import Q
from django.shortcuts import get_object_or_404

from shop.catalog_view_helpers import build_brand_grouped_products_payload, get_brand_by_identifier
from shop.model_utils import transliterate_slug
from shop.models import Brand
from shop.serializers import BrandSerializer, BrandCreateSerializer
from shop.permissions import IsAdmin
from shop.view_transport_helpers import (
    create_instance_from_request,
    require_uploaded_file,
    resolve_request_city,
    update_instance_file_field,
)


@extend_schema(tags=['brands'])
@extend_schema_view(
    get=extend_schema(
        summary='List brands',
        parameters=[
            OpenApiParameter(name='name', description='Filter by name (case-insensitive)', required=False, type=str),
        ],
        responses={200: BrandSerializer(many=True)}
    )
)
class BrandListView(ListAPIView):
    """List all brands with optional name filter"""
    serializer_class = BrandSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = Brand.objects.all()
        name = self.request.query_params.get('name')
        if name:
            transliterated = transliterate_slug(name)
            queryset = queryset.filter(
                Q(name__icontains=name)
                | Q(slug__icontains=name)
                | Q(search_synonyms__contains=[name])
                | Q(name__icontains=transliterated)
                | Q(slug__icontains=transliterated)
                | Q(search_synonyms__contains=[transliterated])
            )
        return queryset


@extend_schema(tags=['brands'])
class BrandCreateView(CreateAPIView):
    """Create a new brand"""
    serializer_class = BrandCreateSerializer
    permission_classes = [IsAdmin]
    
    @extend_schema(
        request=BrandCreateSerializer,
        responses={200: BrandSerializer}
    )
    def post(self, request):
        brand = create_instance_from_request(BrandCreateSerializer, request)
        return Response(BrandSerializer(brand).data)


@extend_schema(tags=['brands'])
class BrandUploadMediaView(APIView):
    """Upload media file for a brand"""
    permission_classes = [IsAdmin]
    
    @extend_schema(
        request={'multipart/form-data': {'type': 'object', 'properties': {'file': {'type': 'string', 'format': 'binary'}}}},
        responses={200: BrandSerializer}
    )
    def post(self, request, brand_id):
        brand = get_object_or_404(Brand, id=brand_id)
        try:
            upload = require_uploaded_file(request)
        except Exception as exc:
            return Response({"detail": exc.detail.get("file", ["No file provided"])[0]}, status=status.HTTP_400_BAD_REQUEST)
        update_instance_file_field(brand, upload, f"brand_{brand_id}")

        return Response(BrandSerializer(brand).data)


@extend_schema(tags=['brands'])
class BrandProductsGroupedView(APIView):
    """Get brand with products grouped by category"""
    permission_classes = [AllowAny]
    
    @extend_schema(
        responses={200: {
            'type': 'object',
            'properties': {
                'brand': {'type': 'object'},
                'categories': {'type': 'array'}
            }
        }}
    )
    def get(self, request, brand_identifier):
        brand = get_brand_by_identifier(brand_identifier)
        city = resolve_request_city(request)

        return Response(build_brand_grouped_products_payload(brand, city=city))
