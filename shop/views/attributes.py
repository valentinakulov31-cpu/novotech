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

from shop.models import Characteristic, ProductCharacteristic, Product
from shop.serializers import CharacteristicSerializer, ProductCharacteristicCreateSerializer, ProductCharacteristicSerializer
from shop.permissions import IsAdmin


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
        product_chars = ProductCharacteristic.objects.filter(
            product_id=product_id
        ).select_related('characteristic')
        
        result = []
        for pc in product_chars:
            result.append({
                'attribute_id': pc.characteristic.id,
                'name': pc.characteristic.name,
                'unit': pc.characteristic.unit,
                'value': pc.value,
            })
        
        return Response(result)


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
        serializer = ProductCharacteristicCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        characteristic = get_object_or_404(
            Characteristic,
            id=serializer.validated_data['attribute_id'],
            group=product.group,
        )
        
        pc = ProductCharacteristic.objects.create(
            product=product,
            characteristic=characteristic,
            value=serializer.validated_data.get('value_text')
        )
        
        return Response({
            'id': pc.id,
            'product_id': pc.product_id,
            'characteristic_id': pc.characteristic_id,
            'value': pc.value,
            'created_at': pc.created_at,
        })
