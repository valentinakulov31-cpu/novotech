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
from shop.admin import ensure_single_primary, sync_product_media
from shop.file_utils import save_uploaded_file


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
        
        file = request.FILES.get('file')
        if not file:
            return Response({'detail': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        uploaded = save_uploaded_file(file, f"product_{product_id}")
        last_sort_order = ProductMedia.objects.filter(product=product).order_by('-sort_order').values_list('sort_order', flat=True).first()
        next_sort_order = (last_sort_order + 1) if last_sort_order is not None else 0
        has_existing_media = ProductMedia.objects.filter(product=product).exists()
        media = ProductMedia.objects.create(
            product=product,
            storage_path=uploaded['storage_path'],
            url=uploaded['url'],
            mime_type=uploaded['mime_type'],
            media_kind=uploaded['file_kind'],
            size_bytes=uploaded['size_bytes'],
            sort_order=next_sort_order,
            is_primary=not has_existing_media,
        )
        ensure_single_primary(product)
        sync_product_media(product)
        
        return Response(ProductMediaSerializer(media).data)
