import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from shop.catalog_cache import catalog_cache_version
from shop.models import Brand, City, Group, Product
from shop.seo_builders import build_product_seo, build_group_seo, own_canonical_url
from shop.seo_common import city_prepositional_phrase, truncate
from shop.sitemaps import GroupPagesSitemap, ProductPagesSitemap


class SeoCleanupTests(TestCase):
    def setUp(self):
        self.group = Group.objects.create(name="Теплоизоляция", slug="insulation", seo_title="Supplier group")
        self.brand = Brand.objects.create(name="K-FLEX", slug="k-flex")
        self.product = Product.objects.create(
            name="K-FLEX ST 10", sku="123456789", slug="k-flex-st-10", price=0, currency="RUB",
            group=self.group, brand=self.brand, description="Supplier phone +7 (495) 580 38 90",
            characteristics_html='<table><tr><td>10 мм</td></tr></table>',
            media=["/static/image.png"], seo_title="Supplier title", seo_description="Supplier description",
            seo_canonical_url="https://supplier.invalid/product", seo_robots="noindex,follow",
        )

    def test_preview_does_not_write(self):
        call_command("reset_catalog_seo", stdout=StringIO())
        self.product.refresh_from_db()
        self.assertEqual(self.product.seo_title, "Supplier title")

    def test_apply_requires_backup(self):
        with self.assertRaises(CommandError):
            call_command("reset_catalog_seo", apply=True, stdout=StringIO())

    def test_backup_failure_does_not_change_data(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("shop.management.commands.reset_catalog_seo.os.open", side_effect=OSError("disk full")):
                with self.assertRaises(CommandError):
                    call_command("reset_catalog_seo", apply=True, backup=Path(folder)/"backup.json", stdout=StringIO())
        self.product.refresh_from_db()
        self.assertEqual(self.product.seo_title, "Supplier title")

    def test_public_backup_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder, override_settings(MEDIA_ROOT=folder):
            with self.assertRaises(CommandError):
                call_command("reset_catalog_seo", apply=True, backup=Path(folder)/"backup.json", stdout=StringIO())

    def test_cleanup_preserves_all_non_seo_data_and_robots(self):
        from shop.management.commands.reset_catalog_seo import SEO_FIELDS
        before = Product.objects.values().get(pk=self.product.pk)
        token = catalog_cache_version()
        with tempfile.TemporaryDirectory() as folder:
            backup = Path(folder)/"seo.json"
            call_command("reset_catalog_seo", apply=True, backup=backup, stdout=StringIO())
            saved = json.loads(backup.read_text(encoding="utf-8"))
            self.assertEqual(saved["records"]["shop.product"][0]["seo_title"], "Supplier title")
            # A second run is a no-op and must not overwrite the existing backup.
            original = backup.read_bytes()
            call_command("reset_catalog_seo", apply=True, backup=backup, stdout=StringIO())
            self.assertEqual(backup.read_bytes(), original)
        after = Product.objects.values().get(pk=self.product.pk)
        for key in before:
            if key in SEO_FIELDS:
                self.assertIsNone(after[key])
            else:
                self.assertEqual(before[key], after[key], key)
        self.assertNotEqual(token, catalog_cache_version())
        self.group.refresh_from_db()
        self.assertIsNone(self.group.seo_title)

    def test_fallbacks_use_our_identity_not_supplier_marketing(self):
        self.product.seo_title = self.product.seo_description = None
        seo = build_product_seo(self.product)
        self.assertIn("Новатех", seo["title"])
        self.assertIn(self.product.name, seo["description"])
        self.assertNotIn("495", seo["description"])
        self.assertEqual(seo["canonical_url"], "/product/k-flex-st-10")
        self.assertEqual(seo["robots"], "noindex,follow")
        self.group.seo_title = None
        self.assertIn("Новатех", build_group_seo(self.group)["title"])

    def test_canonical_rejects_external_or_unsafe_urls(self):
        for value in ("https://evil.invalid/p", "//evil.invalid/p", "javascript:alert(1)",
                      "data:text/plain,hi", "\\\\evil.invalid/x", "/x?tracking=1", "/x#tab", "relative", "https://["):
            with self.subTest(value=value):
                self.assertEqual(own_canonical_url(value, "/product/own"), "/product/own")
        for value in ("/product/own", "https://nvt24.ru/product/own", "https://www.nvt24.ru/product/own"):
            self.assertEqual(own_canonical_url(value, "/fallback"), "/product/own")

    def test_unicode_truncation_and_city_phrase(self):
        self.assertEqual(truncate("абвгдеж", 5), "абвг…")
        self.assertEqual(truncate("test", 0), "")
        city = City(name="Красноярск", name_in_prepositional="Красноярске")
        self.assertEqual(city_prepositional_phrase(city), "в Красноярске")

    def test_sitemap_respects_noindex_and_hidden_brands(self):
        self.assertNotIn(self.product, ProductPagesSitemap().items())
        self.group.seo_robots = "noindex,follow"
        self.group.save()
        self.assertNotIn(self.group, GroupPagesSitemap().items())
        self.product.seo_robots = "index,follow"
        self.product.save()
        self.brand.is_hidden = True
        self.brand.save()
        self.assertNotIn(self.product, ProductPagesSitemap().items())
