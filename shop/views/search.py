from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from shop.filtering import parse_bool
from shop.services.global_search import build_global_search_payload


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
        return Response(
            build_global_search_payload(
                query=request.query_params.get("q"),
                city_slug=request.query_params.get("city_slug"),
                debug=bool(parse_bool(request.query_params.get("debug"))),
            )
        )
