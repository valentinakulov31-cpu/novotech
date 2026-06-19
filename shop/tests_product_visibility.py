from decimal import Decimal
from io import BytesIO

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from shop.models import Brand, Group, Product
from shop.services.catalog_import import build_product_export_rows, import_products_from_workbook
from shop.sitemaps import ProductPagesSitemap


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class ProductVisibilityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.group = Group.objects.create(name="Visibility group", slug="visibility-group")
        self.brand = Brand.objects.create(name="Visibility brand", slug="visibility-brand")
        self.visible_product = Product.objects.create(
            sku="VISIBLE-1",
            slug="visible-product",
            name="Visible product",
            price=Decimal("100.00"),
            currency="RUB",
            group=self.group,
            brand=self.brand,
            available=True,
        )
        self.hidden_product = Product.objects.create(
            sku="HIDDEN-1",
            slug="hidden-product",
            name="Hidden product",
            price=Decimal("100.00"),
            currency="RUB",
            group=self.group,
            brand=self.brand,
            available=True,
            is_hidden=True,
        )

    def test_hidden_product_is_excluded_from_public_catalog(self):
        response = self.client.get(reverse("products-list"), {"group_id": self.group.id})

        self.assertEqual(response.status_code, 200)
        slugs = [item["slug"] for item in response.json()]
        self.assertIn(self.visible_product.slug, slugs)
        self.assertNotIn(self.hidden_product.slug, slugs)

    def test_hidden_product_detail_returns_404(self):
        response = self.client.get(reverse("products-detail", kwargs={"product_identifier": self.hidden_product.slug}))

        self.assertEqual(response.status_code, 404)

    def test_hidden_product_is_excluded_from_global_search(self):
        response = self.client.get(reverse("global-search"), {"q": "Hidden product"})

        self.assertEqual(response.status_code, 200)
        skus = [item["sku"] for item in response.json()["results"]["products"]]
        self.assertNotIn(self.hidden_product.sku, skus)

    def test_hidden_product_is_excluded_from_product_sitemap(self):
        slugs = list(ProductPagesSitemap().items().values_list("slug", flat=True))

        self.assertIn(self.visible_product.slug, slugs)
        self.assertNotIn(self.hidden_product.slug, slugs)

    def test_product_export_includes_hidden_flag(self):
        headers, rows = build_product_export_rows(Product.objects.filter(pk=self.hidden_product.pk))
        row_map = dict(zip(headers, rows[0]))

        self.assertIn("is_hidden", headers)
        self.assertTrue(row_map["is_hidden"])

    def test_product_import_accepts_hidden_flag(self):
        from openpyxl import Workbook

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(["sku", "name", "price", "currency", "group_slug", "brand_slug", "is_hidden"])
        worksheet.append(["IMPORT-HIDDEN", "Imported hidden product", "55.00", "RUB", self.group.name, self.brand.name, "true"])
        buffer = BytesIO()
        workbook.save(buffer)
        buffer.seek(0)

        counters, issues = import_products_from_workbook(buffer)
        product = Product.objects.get(sku="IMPORT-HIDDEN")

        self.assertEqual(issues, [])
        self.assertEqual(counters["products_created"], 1)
        self.assertTrue(product.is_hidden)
