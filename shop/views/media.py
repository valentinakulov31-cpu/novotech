"""
Media views
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.shortcuts import get_object_or_404

from shop.models import ProductMedia, Product
from shop.serializers import ProductMediaSerializer
from shop.permissions import IsAdmin
from shop.services.media_assets import create_product_media_from_upload
from shop.view_transport_helpers import require_uploaded_file


@extend_schema(tags=['media'])
@extend_schema_view(
    get=extend_schema(
        summary='List media for a product',
        responses={200: ProductMediaSerializer(many=True)}
    )
)
class ProductMediaListView(ListAPIView):
    """List all media files for a product"""
    serializer_class = ProductMediaSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        product_id = self.kwargs['product_id']
        return ProductMedia.objects.filter(product_id=product_id).order_by('-is_primary', 'sort_order', 'id')


@extend_schema(tags=['media'])
class ProductMediaUploadView(APIView):
    """Upload media file for a product"""
    permission_classes = [IsAdmin]
    
    @extend_schema(
        request={'multipart/form-data': {'type': 'object', 'properties': {'file': {'type': 'string', 'format': 'binary'}}}},
        responses={200: ProductMediaSerializer}
    )
    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        try:
            upload = require_uploaded_file(request)
        except Exception as exc:
            return Response({"detail": exc.detail.get("file", ["No file provided"])[0]}, status=status.HTTP_400_BAD_REQUEST)
        media = create_product_media_from_upload(product, upload)
        
        return Response(ProductMediaSerializer(media).data)
