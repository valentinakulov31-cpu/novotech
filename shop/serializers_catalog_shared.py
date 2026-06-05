from shop.seo import resolve_city


class SeoContextSerializerMixin:
    def _resolved_city(self):
        if hasattr(self, "_cached_city"):
            return self._cached_city
        request = self.context.get("request") if hasattr(self, "context") else None
        city_slug = request.query_params.get("city_slug") if request else None
        self._cached_city = resolve_city(city_slug=city_slug)
        return self._cached_city
