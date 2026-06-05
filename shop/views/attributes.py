"""
Attributes/Characteristics views
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.shortcuts import get_object_or_404

from shop.models import Characteristic, Product
from shop.serializers import CharacteristicSerializer, ProductCharacteristicCreateSerializer, ProductCharacteristicSerializer
from shop.permissions import IsAdmin
from shop.product_attribute_helpers import create_product_attribute_value, serialize_product_attributes
from shop.view_transport_helpers import validate_request_data


@extend_schema(tags=['attributes'])
@extend_schema_view(
    get=extend_schema(
        summary='List characteristics for a group',
        responses={200: CharacteristicSerializer(many=True)}
    )
)
class CharacteristicListView(ListAPIView):
    """List characteristics for a specific group"""
    serializer_class = CharacteristicSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        group_id = self.kwargs['group_id']
        return Characteristic.objects.filter(group_id=group_id)


@extend_schema(tags=['attributes'])
class ProductAttributesView(APIView):
    """Get attributes for a product"""
    permission_classes = [AllowAny]
    
    @extend_schema(
        responses={200: ProductCharacteristicSerializer(many=True)}
    )
    def get(self, request, product_id):
        return Response(serialize_product_attributes(product_id))


@extend_schema(tags=['attributes'])
class ProductAttributeCreateView(APIView):
    """Create/update product attribute"""
    permission_classes = [IsAdmin]
    
    @extend_schema(
        request=ProductCharacteristicCreateSerializer,
        responses={200: {'type': 'object'}}
    )
    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        payload = validate_request_data(ProductCharacteristicCreateSerializer, request)

        pc = create_product_attribute_value(
            product,
            attribute_id=payload["attribute_id"],
            value=payload.get("value_text"),
        )
        
        return Response({
            'id': pc.id,
            'product_id': pc.product_id,
            'characteristic_id': pc.characteristic_id,
            'value': pc.value,
            'created_at': pc.created_at,
        })
