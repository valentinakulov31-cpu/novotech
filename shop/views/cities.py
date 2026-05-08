from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny

from shop.models import City
from shop.serializers import CitySerializer


@extend_schema(tags=["cities"])
@extend_schema_view(
    get=extend_schema(
        summary="List active cities for geo SEO pages",
        responses={200: CitySerializer(many=True)},
    )
)
class CityListView(ListAPIView):
    serializer_class = CitySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return City.objects.filter(is_active=True).order_by("sort_order", "name", "id")
