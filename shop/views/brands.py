"""
Brand views
"""
import os
from datetime import datetime, timezone as tz
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, CreateAPIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404

from shop.seo import build_group_seo, build_product_seo, resolve_city
from shop.models import Brand, Product, Group, transliterate_slug
from shop.serializers import BrandSerializer, BrandCreateSerializer
from shop.permissions import IsAdmin


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
        serializer = BrandCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        brand = Brand.objects.create(**serializer.validated_data)
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
        
        file = request.FILES.get('file')
        if not file:
            return Response({'detail': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Save file
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        filename = f"brand_{brand_id}_{int(datetime.now(tz.utc).timestamp())}_{file.name}"
        storage_path = os.path.join(settings.MEDIA_ROOT, filename)
        
        with open(storage_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        
        # Update brand
        media_url = f"/static/{filename}"
        brand.media = media_url
        brand.save()
        
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
        # Resolve brand by ID or slug
        if brand_identifier.isdigit():
            brand = get_object_or_404(Brand, id=int(brand_identifier))
        else:
            brand = get_object_or_404(Brand, slug=brand_identifier)
        city = resolve_city(city_slug=request.query_params.get('city_slug'))
        
        # Get products with their groups
        products = Product.objects.filter(brand=brand).select_related('group')
        
        # Group by category
        grouped = {}
        for product in products:
            if product.group:
                category_key = product.group.slug
                if category_key not in grouped:
                    grouped[category_key] = {
                        'id': product.group.id,
                        'slug': product.group.slug,
                        'name': product.group.name,
                        'parent_id': product.group.parent_id,
                        'seo': build_group_seo(product.group, city=city),
                        'products': []
                    }
            else:
                category_key = 'uncategorized'
                if category_key not in grouped:
                    grouped[category_key] = {
                        'id': None,
                        'slug': None,
                        'name': None,
                        'parent_id': None,
                        'products': []
                    }
            
            grouped[category_key]['products'].append({
                'id': product.id,
                'sku': product.sku,
                'slug': product.slug,
                'name': product.name,
                'price': float(product.price),
                'currency': product.currency,
                'description': product.description,
                'group_id': product.group_id,
                'brand_id': product.brand_id,
                'group_slug': product.group.slug if product.group else None,
                'brand_slug': brand.slug,
                'media': product.media,
                'available': product.available,
                'seo': build_product_seo(product, city=city),
            })
        
        return Response({
            'brand': {
                'id': brand.id,
                'name': brand.name,
                'slug': brand.slug,
                'media': brand.media,
            },
            'categories': list(grouped.values())
        })
