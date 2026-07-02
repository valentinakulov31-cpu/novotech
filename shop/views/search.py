import hashlib

from django.core.cache import cache
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from shop.filtering import parse_bool
from shop.services.global_search import build_global_search_payload

SEARCH_CACHE_TTL = 60


def build_search_cache_key(query: str | None, city_slug: str | None) -> str:
    seed = f"{(query or '').strip().lower()}|{(city_slug or '').strip().lower()}".encode("utf-8")
    return f"search:v2:{hashlib.sha256(seed).hexdigest()}"


@extend_schema(
    tags=["search"],
    parameters=[
        OpenApiParameter(name="q", description="Global search query", required=True, type=str),
        OpenApiParameter(name="debug", description="Include search debug details", required=False, type=bool),
    ],
    responses={200: {"type": "object"}},
)
class GlobalSearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get("q")
        city_slug = request.query_params.get("city_slug")
        debug = bool(parse_bool(request.query_params.get("debug")))

        if not debug:
            cache_key = build_search_cache_key(query=query, city_slug=city_slug)
            cached_payload = cache.get(cache_key)
            if cached_payload is not None:
                return Response(cached_payload)

        payload = build_global_search_payload(
            query=query,
            city_slug=city_slug,
            debug=debug,
        )
        if not debug:
            cache.set(cache_key, payload, SEARCH_CACHE_TTL)
        return Response(payload)
