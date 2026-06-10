"""
URL configuration for django_shop project.
"""
from django.contrib import admin
from django.contrib.sitemaps.views import index as sitemap_index_view, sitemap as sitemap_section_view
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from shop.seo_views import robots_txt
from shop.sitemaps import SITEMAPS

urlpatterns = [
    path('robots.txt', robots_txt, name='robots-txt'),
    path(
        'sitemap.xml',
        sitemap_index_view,
        {'sitemaps': SITEMAPS, 'sitemap_url_name': 'sitemap-section'},
        name='sitemap-index',
    ),
    path('sitemap-<section>.xml', sitemap_section_view, {'sitemaps': SITEMAPS}, name='sitemap-section'),
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
