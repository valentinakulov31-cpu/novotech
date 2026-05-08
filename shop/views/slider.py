from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny

from shop.models import Slider, PUBLISH_STATUS_PUBLISHED
from shop.serializers import SliderSerializer


@extend_schema(tags=['slider'])
@extend_schema_view(
    get=extend_schema(
        summary='List active slider items',
        responses={200: SliderSerializer(many=True)}
    )
)
class SliderListView(ListAPIView):
    serializer_class = SliderSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Slider.objects.filter(status=PUBLISH_STATUS_PUBLISHED).order_by('sort_order', 'id')
