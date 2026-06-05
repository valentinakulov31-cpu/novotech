from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from shop.models import Product, ProductCertificate
from shop.permissions import IsAdmin
from shop.serializers import ProductCertificateSerializer
from shop.services.media_assets import create_product_certificate_from_upload
from shop.view_transport_helpers import require_uploaded_file


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
        try:
            upload = require_uploaded_file(request)
        except Exception as exc:
            return Response({"detail": exc.detail.get("file", ["No file provided"])[0]}, status=status.HTTP_400_BAD_REQUEST)

        certificate = create_product_certificate_from_upload(
            product,
            upload,
            title=request.data.get("title"),
            sort_order=request.data.get("sort_order"),
        )
        return Response(ProductCertificateSerializer(certificate).data)
