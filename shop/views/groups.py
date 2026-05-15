"""
Group/Category views
"""
import os
from datetime import datetime, timezone as tz
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, CreateAPIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.conf import settings
from django.shortcuts import get_object_or_404

from shop.seo import build_group_seo, build_product_seo, resolve_city
from shop.models import Group, Product
from shop.serializers import GroupSerializer, GroupCreateSerializer
from shop.permissions import IsAdmin


def build_tree(groups, city=None):
    """Build hierarchical tree from flat list of groups"""
    id_to_node = {g.id: {
        'id': g.id,
        'parent_id': g.parent_id,
        'name': g.name,
        'slug': g.slug,
        'description': g.description,
        'media': g.media,
        'seo': build_group_seo(g, city=city),
        'children': []
    } for g in groups}
    
    roots = []
    for g in groups:
        node = id_to_node[g.id]
        if g.parent_id and g.parent_id in id_to_node:
            id_to_node[g.parent_id]['children'].append(node)
        else:
            roots.append(node)
    
    return roots


@extend_schema(tags=['groups'])
@extend_schema_view(
    get=extend_schema(
        summary='List all groups',
        responses={200: GroupSerializer(many=True)}
    )
)
class GroupListView(ListAPIView):
    """List all groups"""
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [AllowAny]


@extend_schema(tags=['groups'])
class GroupTreeView(APIView):
    """Get groups as hierarchical tree"""
    permission_classes = [AllowAny]
    
    @extend_schema(
        responses={200: {'type': 'array'}}
    )
    def get(self, request):
        groups = Group.objects.all()
        city = resolve_city(city_slug=request.query_params.get('city_slug'))
        tree = build_tree(groups, city=city)
        return Response(tree)


@extend_schema(tags=['groups'])
class GroupCreateView(CreateAPIView):
    """Create a new group"""
    serializer_class = GroupCreateSerializer
    permission_classes = [IsAdmin]
    
    @extend_schema(
        request=GroupCreateSerializer,
        responses={200: GroupSerializer}
    )
    def post(self, request):
        serializer = GroupCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data.copy()
        parent_id = data.pop('parent_id', None)
        
        group = Group.objects.create(
            parent_id=parent_id,
            **data
        )
        
        return Response(GroupSerializer(group).data)


@extend_schema(tags=['groups'])
class GroupUploadMediaView(APIView):
    """Upload media file for a group"""
    permission_classes = [IsAdmin]
    
    @extend_schema(
        request={'multipart/form-data': {'type': 'object', 'properties': {'file': {'type': 'string', 'format': 'binary'}}}},
        responses={200: GroupSerializer}
    )
    def post(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        
        file = request.FILES.get('file')
        if not file:
            return Response({'detail': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Save file
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        filename = f"group_{group_id}_{int(datetime.now(tz.utc).timestamp())}_{file.name}"
        storage_path = os.path.join(settings.MEDIA_ROOT, filename)
        
        with open(storage_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        
        # Update group
        media_url = f"/static/{filename}"
        group.media = media_url
        group.save()
        
        return Response(GroupSerializer(group).data)


@extend_schema(tags=['groups'])
class GroupWithProductsView(APIView):
    """Get group with its products"""
    permission_classes = [AllowAny]
    
    @extend_schema(
        responses={200: {
            'type': 'object',
            'properties': {
                'category': {'type': 'object'},
                'products': {'type': 'array'}
            }
        }}
    )
    def get(self, request, group_identifier):
        # Resolve group by ID or slug
        if group_identifier.isdigit():
            group = get_object_or_404(Group, id=int(group_identifier))
        else:
            group = get_object_or_404(Group, slug=group_identifier)
        city = resolve_city(city_slug=request.query_params.get('city_slug'))
        
        # Get products
        products = Product.objects.filter(group=group)
        
        products_list = [{
            'id': p.id,
            'sku': p.sku,
            'slug': p.slug,
            'name': p.name,
            'price': float(p.price),
            'currency': p.currency,
            'description': p.description,
            'group_id': p.group_id,
            'brand_id': p.brand_id,
            'group_slug': group.slug,
            'brand_slug': p.brand.slug if p.brand else None,
            'media': p.media,
            'available': p.available,
            'seo': build_product_seo(p, city=city),
        } for p in products]
        
        return Response({
            'category': {
                'id': group.id,
                'parent_id': group.parent_id,
                'name': group.name,
                'slug': group.slug,
                'description': group.description,
                'media': group.media,
                'seo': build_group_seo(group, city=city),
            },
            'products': products_list
        })
