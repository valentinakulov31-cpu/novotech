"""
URL configuration for django_shop project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path(settings.ADMIN_URL_PATH, admin.site.urls),
    path('tinymce/', include('tinymce.urls')),
    
    # API endpoints
    path('v1/', include('shop.urls')),
    
    # Swagger/OpenAPI
    path('v1/openapi.json', SpectacularAPIView.as_view(), name='schema'),
    path('v1/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    # Health check
    path('v1/healthz/', lambda request: JsonResponse({'status': 'ok'})),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
