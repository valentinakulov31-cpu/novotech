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
        serializer = NewsCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payload = serializer.validated_data
        if payload.get('status') == PUBLISH_STATUS_PUBLISHED and not payload.get('published_at'):
            from django.utils import timezone
            payload['published_at'] = timezone.now()
        if request.user.is_authenticated:
            payload['updated_by'] = request.user

        news = News.objects.create(**payload)
        return Response(NewsSerializer(news).data)
