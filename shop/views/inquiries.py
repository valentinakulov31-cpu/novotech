import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from shop.serializers import InquiryCreateSerializer, InquirySerializer
from shop.services.order_email import send_inquiry_notification
from shop.view_transport_helpers import create_instance_from_request


logger = logging.getLogger(__name__)


@extend_schema(
    tags=['inquiries'],
    request=InquiryCreateSerializer,
    responses={201: InquirySerializer},
)
class InquiryCreateView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        inquiry = create_instance_from_request(InquiryCreateSerializer, request)
        try:
            send_inquiry_notification(inquiry)
        except Exception:
            logger.exception("Failed to send inquiry notification for inquiry_id=%s", inquiry.id)
        return Response(InquirySerializer(inquiry).data, status=status.HTTP_201_CREATED)
