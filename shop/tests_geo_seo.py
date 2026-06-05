from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from shop.models import Brand, City, Group, Product


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class GeoSeoApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.city = City.objects.create(
            name="РљСЂР°СЃРЅРѕСЏСЂСЃРє",
            slug="krasnoyarsk",
            name_in_prepositional="РљСЂР°СЃРЅРѕСЏСЂСЃРєРµ",
            sort_order=1,
            is_active=True,
        )
        self.group = Group.objects.create(name="РўРµРїР»РѕРёР·РѕР»СЏС†РёСЏ", slug="teploizolyatsiya-geo")
        self.brand = Brand.objects.create(name="ENERGOROLL", slug="energoroll-geo")
        self.product = Product.objects.create(
            sku="GEO-1",
            name="Р¦РёР»РёРЅРґСЂС‹ ENERGOROLL GEO",
            price=Decimal("100.00"),
            currency="RUB",
            description="РўРµРїР»РѕРёР·РѕР»СЏС†РёСЏ РґР»СЏ РіРµРѕ-СЃС‚СЂР°РЅРёС†",
            group=self.group,
            brand=self.brand,
            available=True,
        )

    def test_cities_endpoint_returns_active_cities(self):
        response = self.client.get(reverse("cities-list"))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data[0]["slug"], "krasnoyarsk")
        self.assertEqual(data[0]["name_in_prepositional"], "РљСЂР°СЃРЅРѕСЏСЂСЃРєРµ")

    def test_product_detail_returns_city_aware_seo(self):
        response = self.client.get(
            reverse("products-detail", kwargs={"product_identifier": self.product.slug}),
            {"city_slug": "krasnoyarsk"},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["seo"]["city"], "krasnoyarsk")
        self.assertIn(self.brand.name, data["seo"]["title"])
        self.assertEqual(data["seo"]["canonical_url"], f"/products/{self.product.slug}")

    def test_product_seo_templates_render_city_placeholders(self):
        self.product.seo_title = "{name} РєСѓРїРёС‚СЊ {city_prep} | {brand}"
        self.product.seo_description = "{name} {city_prep} СЃРѕ СЃРєР»Р°РґР°"
        self.product.seo_canonical_url = "/geo/{city_slug}/products/{slug}"
        self.product.save(update_fields=["seo_title", "seo_description", "seo_canonical_url"])

        response = self.client.get(
            reverse("products-detail", kwargs={"product_identifier": self.product.slug}),
            {"city_slug": "krasnoyarsk"},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn(self.product.name, data["seo"]["title"])
        self.assertIn(self.brand.name, data["seo"]["title"])
        self.assertIn(self.city.name_in_prepositional, data["seo"]["description"])
        self.assertEqual(data["seo"]["canonical_url"], f"/geo/krasnoyarsk/products/{self.product.slug}")

    def test_group_detail_returns_city_aware_seo(self):
        response = self.client.get(
            reverse("groups-detail", kwargs={"group_identifier": self.group.slug}),
            {"city_slug": "krasnoyarsk"},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["category"]["seo"]["city"], "krasnoyarsk")
        self.assertIn(self.group.name, data["category"]["seo"]["title"])
        self.assertEqual(data["category"]["seo"]["canonical_url"], f"/groups/{self.group.slug}")

    def test_search_returns_city_aware_seo(self):
        response = self.client.get(
            reverse("global-search"),
            {"q": "ENERGOROLL", "city_slug": "krasnoyarsk"},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["results"]["products"][0]["seo"]["city"], "krasnoyarsk")
        self.assertIn(self.brand.name, data["results"]["products"][0]["seo"]["title"])

    def test_catalog_results_return_city_aware_seo(self):
        response = self.client.post(
            reverse("catalog-results"),
            {
                "context": {
                    "group_slug": self.group.slug,
                    "city_slug": "krasnoyarsk",
                },
                "filters": {},
                "page": 1,
                "page_size": 12,
                "sort": "relevance",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["results"][0]["seo"]["city"], "krasnoyarsk")
        self.assertIn(self.brand.name, data["results"][0]["seo"]["title"])
