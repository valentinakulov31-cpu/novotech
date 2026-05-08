from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from shop.file_utils import save_uploaded_file
from shop.models import Product, ProductCertificate
from shop.permissions import IsAdmin
from shop.serializers import ProductCertificateSerializer


@extend_schema(tags=['product-certificates'])
@extend_schema_view(
    get=extend_schema(
        summary='List certificates for a product',
        responses={200: ProductCertificateSerializer(many=True)}
    )
)
class ProductCertificateListView(ListAPIView):
    serializer_class = ProductCertificateSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        product_id = self.kwargs['product_id']
        return ProductCertificate.objects.filter(product_id=product_id).order_by('sort_order', 'id')


@extend_schema(tags=['product-certificates'])
class ProductCertificateUploadView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        request={'multipart/form-data': {'type': 'object', 'properties': {
            'file': {'type': 'string', 'format': 'binary'},
            'title': {'type': 'string'},
            'sort_order': {'type': 'integer'},
        }}},
        responses={200: ProductCertificateSerializer}
    )
    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        file = request.FILES.get('file')
        if not file:
            return Response({'detail': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        uploaded = save_uploaded_file(file, f"cert_{product_id}")
        sort_order = request.data.get('sort_order')
        if sort_order is None or str(sort_order).strip() == '':
            last_sort_order = ProductCertificate.objects.filter(product=product).order_by('-sort_order').values_list('sort_order', flat=True).first()
            sort_order = (last_sort_order + 1) if last_sort_order is not None else 0

        certificate = ProductCertificate.objects.create(
            product=product,
            title=(request.data.get('title') or file.name).strip(),
            storage_path=uploaded['storage_path'],
            url=uploaded['url'],
            mime_type=uploaded['mime_type'],
            size_bytes=uploaded['size_bytes'],
            sort_order=int(sort_order),
        )
        return Response(ProductCertificateSerializer(certificate).data)
