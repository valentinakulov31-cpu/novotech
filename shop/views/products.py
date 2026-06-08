"""
Product views
"""
import hashlib

from django.core.cache import cache
from rest_framework.generics import ListAPIView, CreateAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter

from shop.catalog_view_helpers import get_product_by_identifier
from shop.filtering import (
    apply_catalog_filters,
    build_facets,
    build_filter_payload_from_query_params,
    parse_bool,
    serialize_product_card,
)
from shop.product_presenters import serialize_product_detail_payload
from shop.models import Product
from shop.serializers import (
    ProductSerializer,
    ProductCreateSerializer,
)
from shop.permissions import IsAdmin
from shop.view_transport_helpers import (
    create_instance_from_request,
    resolve_city_slug,
    resolve_request_city,
    update_instance_from_request,
)


POPULAR_PRODUCTS_CACHE_TTL = 50 * 60


def build_popular_products_cache_key(query_params):
    normalized_params = sorted(
        (key, tuple(values))
        for key, values in query_params.lists()
    )
    cache_seed = repr(normalized_params).encode("utf-8")
    return f"products:popular:v1:{hashlib.sha256(cache_seed).hexdigest()}"


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
            OpenApiParameter(name='popular', description='Return 4 random products', required=False, type=bool),
            OpenApiParameter(name='attr.<slug>', description='Repeatable attribute filter, comma separated values allowed', required=False, type=str),
        ],
        responses={200: ProductSerializer(many=True)}
    )
)
class ProductListView(ListAPIView):
    """List products with optional filters"""
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

    def list(self, request, *args, **kwargs):
        if parse_bool(request.query_params.get('popular')) is True:
            cache_key = build_popular_products_cache_key(request.query_params)
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                return Response(cached_data)

            queryset = self.filter_queryset(self.get_queryset())
            serializer = self.get_serializer(queryset, many=True)
            data = serializer.data
            cache.set(cache_key, data, POPULAR_PRODUCTS_CACHE_TTL)
            return Response(data)

        return super().list(request, *args, **kwargs)
    
    def get_queryset(self):
        payload = build_filter_payload_from_query_params(self.request.query_params)
        queryset = apply_catalog_filters(
            Product.objects.select_related('group', 'brand', 'shared_gallery').prefetch_related(
                'media_files',
                'gallery_items',
                'certificates',
                'shared_gallery__items',
            ),
            payload,
        )
        if parse_bool(self.request.query_params.get('popular')) is True:
            return queryset.order_by('?')[:4]
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
        city_slug = (payload.get("context") or {}).get("city_slug") or payload.get("city_slug")
        city = resolve_city_slug(city_slug) if city_slug else resolve_request_city(request, query_param="city_slug")
        queryset = apply_catalog_filters(
            Product.objects.select_related('group', 'brand', 'shared_gallery').prefetch_related(
                'media_files',
                'gallery_items',
                'certificates',
                'shared_gallery__items',
            ),
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
        product = create_instance_from_request(ProductCreateSerializer, request)
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
        city = resolve_request_city(request)

        return Response(serialize_product_detail_payload(product, city=city))

    @extend_schema(
        request=ProductCreateSerializer,
        responses={200: ProductSerializer}
    )
    def put(self, request, product_identifier):
        product = get_product_by_identifier(product_identifier)
        update_instance_from_request(product, ProductCreateSerializer, request)

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
        update_instance_from_request(product, ProductCreateSerializer, request)
        return Response(ProductSerializer(product).data)
