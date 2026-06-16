from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.test.client import RequestFactory
from django.urls import reverse
from rest_framework.test import APIClient

from shop.filtering_search_parsing import tokenize_query
from shop.filtering_search_ranking import _word_matches_variant
from shop.models import Brand, Characteristic, Group, Product, ProductCharacteristic
from shop.model_slug_utils import transliterate_slug
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


    def test_global_search_ignores_single_character_variant_from_hyphenated_query(self):
        response = self.client.get(reverse("global-search"), {"q": "k-flex"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(any(item["sku"] == "FUZZY-1" for item in data["results"]["products"]))

    def test_global_search_prefers_full_hyphenated_match_over_partial_tail_match(self):
        exact_brand = Brand.objects.create(name="K-FLEX", slug="k-flex")
        partial_brand = Brand.objects.create(name="Acoustic Group", slug="acoustic-group")
        exact_product = Product.objects.create(
            sku="KFLEX-1",
            name="K-FLEX ST",
            slug="k-flex-st",
            price=Decimal("100.00"),
            currency="RUB",
            brand=exact_brand,
            available=True,
        )
        partial_product = Product.objects.create(
            sku="FLEX-1",
            name="FLEXAKUSTIK PIR-50",
            slug="flexakustik-pir-50",
            price=Decimal("100.00"),
            currency="RUB",
            brand=partial_brand,
            available=True,
        )

        response = self.client.get(reverse("global-search"), {"q": "k-flex", "debug": "1"})
        self.assertEqual(response.status_code, 200)
        data = response.json()

        returned_skus = [item["sku"] for item in data["results"]["products"]]
        self.assertIn(exact_product.sku, returned_skus)
        self.assertIn(partial_product.sku, returned_skus)
        self.assertLess(returned_skus.index(exact_product.sku), returned_skus.index(partial_product.sku))


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


class SearchTokenizationTests(TestCase):
    def test_transliterate_slug_handles_cyrillic(self):
        self.assertEqual(transliterate_slug("говно"), "govno")
        self.assertEqual(transliterate_slug("заявка"), "zayavka")

    def test_tokenize_query_does_not_emit_random_item_fallbacks_for_cyrillic(self):
        tokens = tokenize_query("говно")
        self.assertIn("говно", tokens)
        self.assertIn("govno", tokens)
        self.assertNotIn("item", tokens)
        self.assertFalse(any(token.startswith("item-") for token in tokens))

    def test_global_search_debug_payload_filters_single_character_variant_for_hyphenated_term(self):
        client = APIClient()
        response = client.get(reverse("global-search"), {"q": "k-flex", "debug": "1"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("debug", data)
        self.assertEqual(data["debug"]["token_groups"], [["k-flex", "flex", "kflex"]])

    def test_tokenize_query_keeps_original_variants_for_hyphenated_term(self):
        tokens = tokenize_query("k-flex")
        self.assertIn("k-flex", tokens)
        self.assertIn("k", tokens)
        self.assertIn("flex", tokens)
        self.assertIn("kflex", tokens)

    def test_fuzzy_match_rejects_loose_cyrillic_false_positive(self):
        self.assertFalse(_word_matches_variant("главнае", "гавна"))
