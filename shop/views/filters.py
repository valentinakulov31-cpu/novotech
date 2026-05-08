"""
Filter views
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import OpenApiParameter, extend_schema

from shop.filtering import apply_catalog_filters, build_facets, build_filter_payload_from_query_params
from shop.models import Product


@extend_schema(tags=['filters'])
class GroupFiltersView(APIView):
    """Get available filters for a group"""
    permission_classes = [AllowAny]
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='q', description='Optional search context', required=False, type=str),
            OpenApiParameter(name='brand_id', description='Repeatable brand filter', required=False, type=int),
            OpenApiParameter(name='available', description='Filter by availability', required=False, type=bool),
            OpenApiParameter(name='min_price', description='Minimum price', required=False, type=float),
            OpenApiParameter(name='max_price', description='Maximum price', required=False, type=float),
            OpenApiParameter(name='attr.<slug>', description='Current attribute filters', required=False, type=str),
        ],
        responses={200: {'type': 'object'}}
    )
    def get(self, request, group_id):
        payload = build_filter_payload_from_query_params(request.query_params)
        payload['group_id'] = group_id
        queryset = apply_catalog_filters(Product.objects.select_related('group', 'brand'), payload)
        facets = build_facets(queryset)
        facets['scope'] = {'group_id': group_id}
        facets['count'] = queryset.count()
        return Response(facets)


@extend_schema(tags=['filters'])
class GlobalFiltersView(APIView):
    """Get all available filters"""
    permission_classes = [AllowAny]
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='q', description='Optional search context', required=False, type=str),
            OpenApiParameter(name='group_id', description='Optional group filter', required=False, type=int),
            OpenApiParameter(name='brand_id', description='Repeatable brand filter', required=False, type=int),
            OpenApiParameter(name='available', description='Filter by availability', required=False, type=bool),
            OpenApiParameter(name='min_price', description='Minimum price', required=False, type=float),
            OpenApiParameter(name='max_price', description='Maximum price', required=False, type=float),
            OpenApiParameter(name='attr.<slug>', description='Current attribute filters', required=False, type=str),
        ],
        responses={200: {'type': 'object'}}
    )
    def get(self, request):
        payload = build_filter_payload_from_query_params(request.query_params)
        queryset = apply_catalog_filters(Product.objects.select_related('group', 'brand'), payload)
        facets = build_facets(queryset)
        facets['scope'] = {'group_id': payload.get('group_id')}
        facets['count'] = queryset.count()
        return Response(facets)
