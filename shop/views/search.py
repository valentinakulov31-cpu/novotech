from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from shop.filtering import apply_ranked_search, tokenize_query
from shop.seo import build_group_seo, build_product_seo, resolve_city
from shop.models import Brand, Characteristic, Group, Product


def serialize_brand(brand: Brand) -> dict:
    return {
        "id": brand.id,
        "name": brand.name,
        "slug": brand.slug,
        "media": brand.media,
        "url": f"/brands/{brand.slug}",
    }


def serialize_group(group: Group, city=None) -> dict:
    return {
        "id": group.id,
        "parent_id": group.parent_id,
        "name": group.name,
        "slug": group.slug,
        "description": group.description,
        "media": group.media,
        "seo": build_group_seo(group, city=city),
        "url": f"/groups/{group.slug}",
    }


def serialize_product(product: Product, city=None) -> dict:
    return {
        "id": product.id,
        "sku": product.sku,
        "slug": product.slug,
        "name": product.name,
        "price": float(product.price),
        "currency": product.currency,
        "description": product.description,
        "group_id": product.group_id,
        "brand_id": product.brand_id,
        "media": product.media,
        "available": product.available,
        "seo": build_product_seo(product, city=city),
        "group": serialize_group(product.group, city=city) if product.group else None,
        "brand": serialize_brand(product.brand) if product.brand else None,
        "url": f"/products/{product.slug}",
    }


def serialize_characteristic(characteristic: Characteristic, city=None) -> dict:
    return {
        "id": characteristic.id,
        "group_id": characteristic.group_id,
        "name": characteristic.name,
        "slug": characteristic.slug,
        "data_type": characteristic.data_type,
        "unit": characteristic.unit,
        "is_filterable": characteristic.is_filterable,
        "is_searchable": characteristic.is_searchable,
        "group": serialize_group(characteristic.group, city=city),
    }


@extend_schema(
    tags=["search"],
    parameters=[
        OpenApiParameter(name="q", description="Global search query", required=True, type=str),
    ],
    responses={200: {"type": "object"}},
)
class GlobalSearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = (request.query_params.get("q") or "").strip()
        city = resolve_city(city_slug=request.query_params.get("city_slug"))
        tokens = tokenize_query(query)
        if not tokens:
            return Response(
                {
                    "query": query,
                    "tokens": [],
                    "navigation": {"group": None, "brand": None, "mode": None},
                    "results": {
                        "products": [],
                        "groups": [],
                        "brands": [],
                        "characteristics": [],
                    },
                }
            )

        product_fields = [
            "sku",
            "slug",
            "name",
            "description",
            "characteristics_html",
            "search_tsv",
            "group__name",
            "group__slug",
            "brand__name",
            "brand__slug",
            "characteristics__value",
            "characteristics__characteristic__name",
            "characteristics__characteristic__slug",
        ]
        group_fields = ["name", "slug", "description"]
        brand_fields = ["name", "slug"]
        characteristic_fields = ["name", "slug", "group__name", "group__slug"]

        products = (
            apply_ranked_search(
                Product.objects.select_related("group", "brand"),
                query,
                exact_fields=product_fields,
                fuzzy_fields=product_fields,
                require_all_tokens=True,
            )
            .distinct()
            .order_by("-search_rank", "-search_similarity", "name")[:30]
        )

        groups = (
            apply_ranked_search(
                Group.objects.all(),
                query,
                exact_fields=group_fields,
                fuzzy_fields=group_fields,
                require_all_tokens=False,
            )
            .order_by("-search_rank", "-search_similarity", "name")[:10]
        )

        brands = (
            apply_ranked_search(
                Brand.objects.all(),
                query,
                exact_fields=brand_fields,
                fuzzy_fields=brand_fields,
                require_all_tokens=False,
            )
            .order_by("-search_rank", "-search_similarity", "name")[:10]
        )

        characteristics = (
            apply_ranked_search(
                Characteristic.objects.select_related("group"),
                query,
                exact_fields=characteristic_fields,
                fuzzy_fields=characteristic_fields,
                require_all_tokens=False,
            )
            .order_by("-search_rank", "-search_similarity", "name")[:15]
        )

        top_group = groups[0] if groups else None
        top_brand = brands[0] if brands else None

        mode = None
        if top_group and top_brand:
            mode = "group_brand"
        elif top_group:
            mode = "group"
        elif top_brand:
            mode = "brand"

        return Response(
            {
                "query": query,
                "tokens": tokens,
                "navigation": {
                    "mode": mode,
                    "group": serialize_group(top_group, city=city) if top_group else None,
                    "brand": serialize_brand(top_brand) if top_brand else None,
                },
                "results": {
                    "products": [serialize_product(product, city=city) for product in products],
                    "groups": [serialize_group(group, city=city) for group in groups],
                    "brands": [serialize_brand(brand) for brand in brands],
                    "characteristics": [serialize_characteristic(characteristic, city=city) for characteristic in characteristics],
                },
            }
        )
