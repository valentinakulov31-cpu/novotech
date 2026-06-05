from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.test.client import RequestFactory
from django.urls import reverse
from rest_framework.test import APIClient

from shop.models import Brand, Characteristic, Group, Product, ProductCharacteristic
from shop.permissions import IsAdmin


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class GlobalSearchFuzzyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.group = Group.objects.create(name="РўРµРїР»РѕРёР·РѕР»СЏС†РёСЏ", slug="teploizolyatsiya-fuzzy")
        self.brand = Brand.objects.create(name="ENERGOROLL", slug="energoroll-fuzzy")
        self.product = Product.objects.create(
            sku="FUZZY-1",
            name="Р¦РёР»РёРЅРґСЂС‹ ENERGOROLL RK",
            price=Decimal("150.00"),
            currency="RUB",
            search_tsv="РјРёРЅРІР°С‚Р°, Р±Р°Р·Р°Р»СЊС‚РѕРІР°СЏ РёР·РѕР»СЏС†РёСЏ, СЌРЅРµСЂРіРѕ СЂРѕР»Р»",
            group=self.group,
            brand=self.brand,
            available=True,
        )
        self.cover_characteristic = Characteristic.objects.create(
            group=self.group,
            name="РџРѕРєСЂС‹С‚РёРµ",
            slug="pokrytie-fuzzy",
            data_type="text",
            is_filterable=True,
        )
        ProductCharacteristic.objects.create(
            product=self.product,
            characteristic=self.cover_characteristic,
            value="Р‘РµР· РїРѕРєСЂС‹С‚РёСЏ",
        )

    def test_global_search_supports_typos(self):
        response = self.client.get(reverse("global-search"), {"q": "ENERGORLL"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(any(item["sku"] == "FUZZY-1" for item in data["results"]["products"]))
        self.assertTrue(any(item["slug"] == "energoroll-fuzzy" for item in data["results"]["brands"]))

    def test_global_search_uses_search_tsv_synonyms(self):
        self.product.search_tsv = "СЌРЅРµСЂРіРѕ СЂРѕР»Р», С†РёР»РёРЅРґСЂС‹ rk, Р±Р°Р·Р°Р»СЊС‚РѕРІР°СЏ РёР·РѕР»СЏС†РёСЏ"
        self.product.save(update_fields=["search_tsv"])

        response = self.client.get(reverse("global-search"), {"q": "Р±Р°Р·Р°Р»СЊС‚РѕРІР°СЏ РёР·РѕР»СЏС†РёСЏ"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(any(item["sku"] == "FUZZY-1" for item in data["results"]["products"]))

    def test_global_search_does_not_duplicate_products_for_characteristic_matches(self):
        response = self.client.get(reverse("global-search"), {"q": "РїРѕРєСЂС‹С‚"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        product_ids = [item["id"] for item in data["results"]["products"]]
        self.assertEqual(len(product_ids), len(set(product_ids)))


class IsAdminPermissionTests(TestCase):
    def test_staff_user_passes_permission(self):
        request = RequestFactory().get("/admin-only")
        request.user = get_user_model().objects.create_user(
            username="staff-user",
            password="secret123",
            is_staff=True,
        )

        self.assertTrue(IsAdmin().has_permission(request, view=None))

    def test_regular_user_is_rejected(self):
        request = RequestFactory().get("/admin-only")
        request.user = get_user_model().objects.create_user(
            username="regular-user",
            password="secret123",
        )

        self.assertFalse(IsAdmin().has_permission(request, view=None))
