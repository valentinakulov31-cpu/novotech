from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny

from shop.models import Agent, PUBLISH_STATUS_PUBLISHED
from shop.serializers import AgentSerializer


@extend_schema(tags=['agents'])
@extend_schema_view(
    get=extend_schema(
        summary='List active agents',
        responses={200: AgentSerializer(many=True)},
    )
)
class AgentListView(ListAPIView):
    serializer_class = AgentSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Agent.objects.filter(status=PUBLISH_STATUS_PUBLISHED).order_by('sort_order', 'id')
