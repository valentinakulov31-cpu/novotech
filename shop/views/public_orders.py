import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from shop.models import PublicOrder
from shop.serializers import PublicOrderCreateSerializer, PublicOrderSerializer
from shop.services.order_email import send_public_order_notification
from shop.services.public_orders import create_public_order


logger = logging.getLogger(__name__)


@extend_schema(tags=['public-orders'])
class PublicOrderCreateView(CreateAPIView):
    """Create a public order request from the website."""

    authentication_classes = []
    serializer_class = PublicOrderCreateSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        request=PublicOrderCreateSerializer,
        responses={201: PublicOrderSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = create_public_order(serializer.validated_data)
        self._send_order_email_notification(order.id)
        return Response(PublicOrderSerializer(order).data, status=status.HTTP_201_CREATED)

    def _send_order_email_notification(self, order_id: int):
        try:
            order = PublicOrder.objects.prefetch_related('items__product').get(id=order_id)
            send_public_order_notification(order)
        except Exception:
            logger.exception('Failed to send public order notification for order_id=%s', order_id)
