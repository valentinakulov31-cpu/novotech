"""
News views
"""
from django.http import Http404
from rest_framework import status
from rest_framework.generics import ListAPIView, CreateAPIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter

from shop.models import News, PUBLISH_STATUS_PUBLISHED
from shop.serializers import NewsSerializer, NewsCreateSerializer
from shop.permissions import IsAdmin
from shop.view_transport_helpers import create_instance_from_request


@extend_schema(tags=['news'])
@extend_schema_view(
    get=extend_schema(
        summary='List news',
        parameters=[
            OpenApiParameter(name='only_published', description='Show only published news', required=False, type=bool, default=True),
        ],
        responses={200: NewsSerializer(many=True)}
    )
)
class NewsListView(ListAPIView):
    """List news with optional published filter"""
    serializer_class = NewsSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = News.objects.prefetch_related('attachments')
        only_published = self.request.query_params.get('only_published', 'true')

        if only_published.lower() == 'false' and getattr(self.request.user, 'is_staff', False):
            return queryset

        queryset = queryset.filter(status=PUBLISH_STATUS_PUBLISHED)
        return queryset


@extend_schema(tags=['news'])
class NewsCreateView(CreateAPIView):
    """Create news"""
    serializer_class = NewsCreateSerializer
    permission_classes = [IsAdmin]
    
    @extend_schema(
        request=NewsCreateSerializer,
        responses={200: NewsSerializer}
    )
    def post(self, request):
        news = create_instance_from_request(NewsCreateSerializer, request, context={"request": request})
        return Response(NewsSerializer(news).data)
