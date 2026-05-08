from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny

from shop.models import Sert, PUBLISH_STATUS_PUBLISHED
from shop.serializers import SertSerializer


@extend_schema(tags=['serts'])
@extend_schema_view(
    get=extend_schema(
        summary='List active sert files',
        responses={200: SertSerializer(many=True)}
    )
)
class SertListView(ListAPIView):
    serializer_class = SertSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Sert.objects.filter(status=PUBLISH_STATUS_PUBLISHED).order_by('sort_order', 'id')
