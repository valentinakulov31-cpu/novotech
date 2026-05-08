from django.http import Http404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny

from shop.models import HtmlContent, PUBLISH_STATUS_PUBLISHED
from shop.serializers import HtmlContentSerializer


@extend_schema(tags=['content'])
@extend_schema_view(
    get=extend_schema(
        summary='Get two HTML blocks for the site',
        responses={200: HtmlContentSerializer},
    )
)
class HtmlContentView(RetrieveAPIView):
    serializer_class = HtmlContentSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        obj = HtmlContent.objects.filter(status=PUBLISH_STATUS_PUBLISHED).order_by('-updated_at', '-id').first()
        if not obj:
            raise Http404("No published HTML content found.")
        return obj
