import logging

from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from shop.models import PublicOrder, PublicOrderItem
from shop.serializers import PublicOrderCreateSerializer, PublicOrderSerializer
from shop.services.order_email import send_public_order_notification


logger = logging.getLogger(__name__)


@extend_schema(tags=['public-orders'])
class PublicOrderCreateView(CreateAPIView):
    """Create a public order request from the website."""

    serializer_class = PublicOrderCreateSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        request=PublicOrderCreateSerializer,
        responses={201: PublicOrderSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            order = PublicOrder.objects.create(
                name=serializer.validated_data['name'],
                phone=serializer.validated_data['phone'],
                email=serializer.validated_data.get('email') or None,
                address=serializer.validated_data.get('address') or None,
                comment=serializer.validated_data.get('comment') or None,
                total_items=sum(item['qty'] for item in serializer.validated_data['items']),
            )
            PublicOrderItem.objects.bulk_create(
                [
                    PublicOrderItem(
                        order=order,
                        product_id=item['product_id'],
                        qty=item['qty'],
                    )
                    for item in serializer.validated_data['items']
                ]
            )

        order.refresh_from_db()
        self._send_order_email_notification(order.id)
        return Response(PublicOrderSerializer(order).data, status=status.HTTP_201_CREATED)

    def _send_order_email_notification(self, order_id: int):
        try:
            order = PublicOrder.objects.prefetch_related('items__product').get(id=order_id)
            send_public_order_notification(order)
        except Exception:
            logger.exception('Failed to send public order notification for order_id=%s', order_id)
