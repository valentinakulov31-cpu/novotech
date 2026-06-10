from django.conf import settings
from django.http import HttpResponse
from django.urls import reverse


def robots_txt(request):
    sitemap_url = request.build_absolute_uri(reverse("sitemap-index"))
    admin_path = settings.ADMIN_URL_PATH
    if not admin_path.startswith("/"):
        admin_path = f"/{admin_path}"
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /v1/",
        "Disallow: /tinymce/",
        "Disallow: /django-static/admin/",
        f"Disallow: {admin_path}",
        f"Sitemap: {sitemap_url}",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain; charset=utf-8")
