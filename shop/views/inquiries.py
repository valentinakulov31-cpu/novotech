from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from shop.serializers import InquiryCreateSerializer, InquirySerializer


@extend_schema(
    tags=['inquiries'],
    request=InquiryCreateSerializer,
    responses={201: InquirySerializer},
)
class InquiryCreateView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = InquiryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inquiry = serializer.save()
        return Response(InquirySerializer(inquiry).data, status=status.HTTP_201_CREATED)
