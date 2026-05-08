from django.http import Http404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny

from shop.models import ContactInfo, PUBLISH_STATUS_PUBLISHED
from shop.serializers import ContactInfoSerializer


@extend_schema(tags=['content'])
@extend_schema_view(
    get=extend_schema(
        summary='Get company contacts',
        responses={200: ContactInfoSerializer},
    )
)
class ContactInfoView(RetrieveAPIView):
    serializer_class = ContactInfoSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        obj = ContactInfo.objects.filter(status=PUBLISH_STATUS_PUBLISHED).order_by('-updated_at', '-id').first()
        if not obj:
            raise Http404("No published contact info found.")
        return obj
