from django.conf import settings


class MediaEmbedHeadersMiddleware:
    ALLOWED_PREFIXES = (
        "/static/admin_uploads/serts/",
        "/static/admin_uploads/product_certificates/",
        "/static/admin_uploads/product_documents/",
    )
    ALLOWED_EXTENSIONS = (".pdf", ".doc", ".docx")

    def __init__(self, get_response):
        self.get_response = get_response

    def _frame_ancestors_value(self):
        configured = getattr(settings, "FRAME_ANCESTOR_ORIGINS", None)
        if isinstance(configured, (list, tuple)):
            configured = " ".join(str(item).strip() for item in configured if str(item).strip())
        configured = str(configured or "").strip()
        return configured or ("*" if settings.DEBUG else "'self'")

    def __call__(self, request):
        response = self.get_response(request)

        media_url = getattr(settings, "MEDIA_URL", "/static/")
        path = request.path or ""
        normalized = path.lower()

        is_allowed_prefix = any(normalized.startswith(prefix.lower()) for prefix in self.ALLOWED_PREFIXES)
        is_allowed_extension = normalized.endswith(self.ALLOWED_EXTENSIONS)

        if path.startswith(media_url) and is_allowed_prefix and is_allowed_extension:
            response.headers.pop("X-Frame-Options", None)
            response["Cross-Origin-Opener-Policy"] = "unsafe-none"
            response["Content-Security-Policy"] = f"frame-ancestors {self._frame_ancestors_value()}"

        return response
