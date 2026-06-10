from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from shop.models import Brand, Group, News, Product, PUBLISH_STATUS_PUBLISHED


@override_settings(
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
    ADMIN_URL_PATH="secret-admin/",
)
class SeoInfraTests(TestCase):
    def setUp(self):
        self.group = Group.objects.create(name="Изоляция", slug="izolyatsiya")
        self.brand = Brand.objects.create(name="NOVATEH", slug="novateh")
        self.product = Product.objects.create(
            sku="SEO-1",
            slug="novateh-seo-product",
            name="NOVATEH SEO Product",
            price=Decimal("100.00"),
            currency="RUB",
            group=self.group,
            brand=self.brand,
            available=True,
        )
        self.news = News.objects.create(
            title="SEO news",
            slug="seo-news",
            content="Published news",
            status=PUBLISH_STATUS_PUBLISHED,
        )

    def test_robots_txt_references_sitemap_and_blocks_technical_paths(self):
        response = self.client.get(reverse("robots-txt"))

        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        self.assertIn("User-agent: *", body)
        self.assertIn("Disallow: /v1/", body)
        self.assertIn("Disallow: /tinymce/", body)
        self.assertIn("Disallow: /secret-admin/", body)
        self.assertIn("Sitemap: http://testserver/sitemap.xml", body)

    def test_sitemap_index_exposes_named_sections(self):
        response = self.client.get(reverse("sitemap-index"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("sitemap-static.xml", content)
        self.assertIn("sitemap-groups.xml", content)
        self.assertIn("sitemap-producers.xml", content)
        self.assertIn("sitemap-products.xml", content)
        self.assertIn("sitemap-news.xml", content)

    def test_products_sitemap_uses_public_frontend_routes(self):
        response = self.client.get(reverse("sitemap-section", kwargs={"section": "products"}))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("/product/novateh-seo-product", content)

    def test_groups_and_producers_sitemaps_use_public_frontend_routes(self):
        group_response = self.client.get(reverse("sitemap-section", kwargs={"section": "groups"}))
        producer_response = self.client.get(reverse("sitemap-section", kwargs={"section": "producers"}))

        self.assertEqual(group_response.status_code, 200)
        self.assertEqual(producer_response.status_code, 200)
        self.assertIn("/group/izolyatsiya", group_response.content.decode("utf-8"))
        self.assertIn("/producer/novateh", producer_response.content.decode("utf-8"))

    def test_news_sitemap_uses_news_detail_route(self):
        response = self.client.get(reverse("sitemap-section", kwargs={"section": "news"}))

        self.assertEqual(response.status_code, 200)
        self.assertIn("/news/seo-news", response.content.decode("utf-8"))
