"""
Group/Category views
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, CreateAPIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.shortcuts import get_object_or_404

from shop.catalog_view_helpers import build_group_tree, build_group_with_products_payload, get_group_by_identifier
from shop.models import Group
from shop.serializers import GroupSerializer, GroupCreateSerializer
from shop.permissions import IsAdmin
from shop.view_transport_helpers import (
    create_instance_from_request,
    require_uploaded_file,
    resolve_request_city,
    update_instance_file_field,
)


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
        city = resolve_request_city(request)
        tree = build_group_tree(groups, city=city)
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
        group = create_instance_from_request(GroupCreateSerializer, request)
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
        try:
            upload = require_uploaded_file(request)
        except Exception as exc:
            return Response({"detail": exc.detail.get("file", ["No file provided"])[0]}, status=status.HTTP_400_BAD_REQUEST)
        update_instance_file_field(group, upload, f"group_{group_id}")

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
        group = get_group_by_identifier(group_identifier)
        city = resolve_request_city(request)

        return Response(build_group_with_products_payload(group, city=city))
