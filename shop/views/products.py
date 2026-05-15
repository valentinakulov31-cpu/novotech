"""
Product views
"""
from rest_framework.generics import ListAPIView, CreateAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from django.shortcuts import get_object_or_404
from django.db.models import Q

from shop.filtering import (
    apply_catalog_filters,
    build_facets,
    build_filter_payload_from_query_params,
    parse_bool,
    serialize_product_card,
)
from shop.seo import build_product_seo, resolve_city
from shop.models import Product, ProductMedia, ProductGalleryItem, ProductCharacteristic, ProductDocument, ProductCertificate
from shop.serializers import (
    ProductSerializer,
    ProductCreateSerializer,
    ProductGalleryItemSerializer,
    ProductDocumentSerializer,
    ProductMediaSerializer,
    ProductCertificateSerializer,
)
from shop.permissions import IsAdmin


def get_product_by_identifier(product_identifier):
    lookup = Q(slug=product_identifier)
    if str(product_identifier).isdigit():
        lookup |= Q(id=int(product_identifier))
    return get_object_or_404(Product, lookup)


@extend_schema(tags=['products'])
@extend_schema_view(
    get=extend_schema(
        summary='List products with filters',
        parameters=[
            OpenApiParameter(name='q', description='Text search across product, brand, group, and characteristics', required=False, type=str),
            OpenApiParameter(name='group_id', description='Filter by group ID', required=False, type=int),
            OpenApiParameter(name='brand_id', description='Filter by brand ID, can be repeated', required=False, type=int),
            OpenApiParameter(name='min_price', description='Minimum price', required=False, type=float),
            OpenApiParameter(name='max_price', description='Maximum price', required=False, type=float),
            OpenApiParameter(name='available', description='Filter by availability', required=False, type=bool),
            OpenApiParameter(name='popular', description='Return 8 random products', required=False, type=bool),
            OpenApiParameter(name='attr.<slug>', description='Repeatable attribute filter, comma separated values allowed', required=False, type=str),
        ],
        responses={200: ProductSerializer(many=True)}
    )
)
class ProductListView(ListAPIView):
    """List products with optional filters"""
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        payload = build_filter_payload_from_query_params(self.request.query_params)
        queryset = apply_catalog_filters(
            Product.objects.select_related('group', 'brand').prefetch_related('media_files', 'gallery_items', 'documents', 'certificates'),
            payload,
        )
        if parse_bool(self.request.query_params.get('popular')) is True:
            return queryset.order_by('?')[:8]
        return queryset


@extend_schema(
    tags=['products'],
    request={'application/json': {'type': 'object'}},
    responses={200: {'type': 'object'}},
)
class ProductFilterView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        payload = request.data or {}
        city = resolve_city(
            city_slug=(payload.get("context") or {}).get("city_slug") or payload.get("city_slug"),
        )
        queryset = apply_catalog_filters(
            Product.objects.select_related('group', 'brand').prefetch_related('media_files', 'gallery_items', 'documents', 'certificates'),
            payload,
        )
        products = [serialize_product_card(product, city=city) for product in queryset.order_by('name')]
        return Response({
            'count': len(products),
            'results': products,
            'applied_filters': payload,
        })


@extend_schema(tags=['products'])
class ProductCreateView(CreateAPIView):
    """Create a new product"""
    serializer_class = ProductCreateSerializer
    permission_classes = [IsAdmin]
    
    @extend_schema(
        request=ProductCreateSerializer,
        responses={200: ProductSerializer}
    )
    def post(self, request):
        serializer = ProductCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data.copy()
        group_id = data.pop('group_id', None)
        brand_id = data.pop('brand_id', None)
        
        product = Product.objects.create(
            group_id=group_id,
            brand_id=brand_id,
            **data
        )
        
        return Response(ProductSerializer(product).data)


@extend_schema(tags=['products'])
class ProductDetailView(APIView):
    """Get product details with media and attributes"""
    permission_classes = [AllowAny]
    
    @extend_schema(
        responses={200: {
            'type': 'object',
            'properties': {
                'id': {'type': 'integer'},
                'sku': {'type': 'string'},
                'slug': {'type': 'string'},
                'name': {'type': 'string'},
                'price': {'type': 'number'},
                'media_list': {'type': 'array'},
                'attributes': {'type': 'array'}
            }
        }}
    )
    def get(self, request, product_identifier):
        product = get_product_by_identifier(product_identifier)
        city = resolve_city(city_slug=request.query_params.get('city_slug'))
        
        # Get media
        media_list = ProductMediaSerializer(
            ProductMedia.objects.filter(product=product).order_by('-is_primary', 'sort_order', 'id'),
            many=True,
        ).data
        gallery = ProductGalleryItemSerializer(
            ProductGalleryItem.objects.filter(product=product).order_by('sort_order', 'id'),
            many=True,
        ).data
        documents_list = ProductDocumentSerializer(
            ProductDocument.objects.filter(product=product).order_by('sort_order', 'id'),
            many=True,
        ).data
        certificates_list = ProductCertificateSerializer(
            ProductCertificate.objects.filter(product=product).order_by('sort_order', 'id'),
            many=True,
        ).data
        
        # Get attributes with characteristic details
        attributes = []
        product_chars = ProductCharacteristic.objects.filter(
            product=product
        ).select_related('characteristic')
        
        for pc in product_chars:
            attributes.append({
                'id': pc.characteristic.id,
                'name': pc.characteristic.name,
                'unit': pc.characteristic.unit,
                'value': pc.value,
            })
        
        return Response({
            'id': product.id,
            'sku': product.sku,
            'slug': product.slug,
            'name': product.name,
            'price': float(product.price),
            'currency': product.currency,
            'description': product.description,
            'assortment_html': product.assortment_html,
            'characteristics_html': product.characteristics_html,
            'group_id': product.group_id,
            'brand_id': product.brand_id,
            'media': product.media,
            'available': product.available,
            'seo': build_product_seo(product, city=city),
            'media_list': media_list,
            'gallery': gallery,
            'documents_list': documents_list,
            'certificates_list': certificates_list,
            'attributes': attributes,
        })

    @extend_schema(
        request=ProductCreateSerializer,
        responses={200: ProductSerializer}
    )
    def put(self, request, product_identifier):
        product = get_product_by_identifier(product_identifier)
        serializer = ProductCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data.copy()
        group_id = data.pop('group_id', None)
        brand_id = data.pop('brand_id', None)

        for key, value in data.items():
            setattr(product, key, value)

        product.group_id = group_id
        product.brand_id = brand_id
        product.save()

        return Response(ProductSerializer(product).data)


@extend_schema(tags=['products'])
class ProductUpdateView(UpdateAPIView):
    """Update a product"""
    serializer_class = ProductCreateSerializer
    permission_classes = [IsAdmin]
    
    @extend_schema(
        request=ProductCreateSerializer,
        responses={200: ProductSerializer}
    )
    def put(self, request, product_identifier):
        product = get_product_by_identifier(product_identifier)
        serializer = ProductCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data.copy()
        group_id = data.pop('group_id', None)
        brand_id = data.pop('brand_id', None)
        
        for key, value in data.items():
            setattr(product, key, value)
        
        product.group_id = group_id
        product.brand_id = brand_id
        product.save()
        
        return Response(ProductSerializer(product).data)
