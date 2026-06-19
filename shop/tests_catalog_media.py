from django.urls import reverse

from shop.models import Product
from shop.tests_catalog_support import CatalogApiFixtureBase


class CatalogMediaApiTests(CatalogApiFixtureBase):
    def test_product_detail_includes_sorted_media_and_documents(self):
        response = self.client.get(reverse("products-detail", kwargs={"product_identifier": self.product.slug}))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["slug"], self.product.slug)
        self.assertEqual([item["url"] for item in data["media_list"]], ["/static/b.jpg", "/static/a.jpg"])
        self.assertEqual([item["url"] for item in data["gallery"]], ["/static/video.mp4", "/static/gallery.jpg"])
        self.assertEqual(data["gallery"][0]["file_kind"], "video")
        self.assertEqual(data["certificates_list"][0]["title"], "Р РЋР ВµРЎР‚РЎвЂљР С‘РЎвЂћР С‘Р С”Р В°РЎвЂљ РЎРѓР С•Р С•РЎвЂљР Р†Р ВµРЎвЂљРЎРѓРЎвЂљР Р†Р С‘РЎРЏ")
        self.assertEqual(data["assortment_html"], "<p><strong>Р С’РЎРѓРЎРѓР С•РЎР‚РЎвЂљР С‘Р СР ВµР Р…РЎвЂљ:</strong> РЎвЂ Р С‘Р В»Р С‘Р Р…Р Т‘РЎР‚РЎвЂ№, Р СР В°РЎвЂљРЎвЂ№</p>")

    def test_products_list_includes_media_documents_and_certificates(self):
        response = self.client.get(reverse("products-list"), {"group_id": self.group.id})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data[0]["gallery"][0]["url"], "/static/video.mp4")
        self.assertEqual(data[0]["gallery"][0]["file_kind"], "video")
        self.assertEqual(data[0]["media_list"][0]["media_kind"], "image")
        self.assertEqual(data[0]["certificates_list"][0]["url"], "/static/certificate.pdf")
        self.assertEqual(data[0]["assortment_html"], "<p><strong>Р С’РЎРѓРЎРѓР С•РЎР‚РЎвЂљР С‘Р СР ВµР Р…РЎвЂљ:</strong> РЎвЂ Р С‘Р В»Р С‘Р Р…Р Т‘РЎР‚РЎвЂ№, Р СР В°РЎвЂљРЎвЂ№</p>")

    def test_hidden_products_are_not_publicly_visible(self):
        hidden_product = Product.objects.create(
            sku="HIDDEN-1",
            slug="hidden-product",
            name="Hidden product",
            price="10.00",
            currency="RUB",
            group=self.group,
            brand=self.brand,
            available=True,
            is_hidden=True,
        )

        list_response = self.client.get(reverse("products-list"), {"group_id": self.group.id})
        self.assertEqual(list_response.status_code, 200)
        returned_slugs = [item["slug"] for item in list_response.json()]
        self.assertNotIn(hidden_product.slug, returned_slugs)

        detail_response = self.client.get(reverse("products-detail", kwargs={"product_identifier": hidden_product.slug}))
        self.assertEqual(detail_response.status_code, 404)

    def test_public_media_payload_does_not_expose_storage_paths(self):
        response = self.client.get(reverse("products-detail", kwargs={"product_identifier": self.product.slug}))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertNotIn("storage_path", data["media_list"][0])
        self.assertNotIn("storage_path", data["gallery"][0])
        self.assertNotIn("storage_path", data["certificates_list"][0])

    def test_products_api_returns_characteristics_html(self):
        detail_response = self.client.get(reverse("products-detail", kwargs={"product_identifier": self.product.slug}))
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(
            detail_response.json()["characteristics_html"],
            "<div><h3>Р ТђР В°РЎР‚Р В°Р С”РЎвЂљР ВµРЎР‚Р С‘РЎРѓРЎвЂљР С‘Р С”Р С‘</h3><p>Р СћР С•Р В»РЎвЂ°Р С‘Р Р…Р В°, Р С—Р С•Р С”РЎР‚РЎвЂ№РЎвЂљР С‘Р Вµ</p></div>",
        )

        list_response = self.client.get(reverse("products-list"), {"group_id": self.group.id})
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(
            list_response.json()[0]["characteristics_html"],
            "<div><h3>Р ТђР В°РЎР‚Р В°Р С”РЎвЂљР ВµРЎР‚Р С‘РЎРѓРЎвЂљР С‘Р С”Р С‘</h3><p>Р СћР С•Р В»РЎвЂ°Р С‘Р Р…Р В°, Р С—Р С•Р С”РЎР‚РЎвЂ№РЎвЂљР С‘Р Вµ</p></div>",
        )

    def test_product_and_group_endpoints_include_seo_payload(self):
        product_detail = self.client.get(reverse("products-detail", kwargs={"product_identifier": self.product.slug}))
        self.assertEqual(product_detail.status_code, 200)
        product_data = product_detail.json()
        self.assertIn("seo", product_data)
        self.assertEqual(product_data["seo"]["h1"], self.product.name)
        self.assertEqual(product_data["seo"]["canonical_url"], f"/products/{self.product.slug}")

        group_list = self.client.get(reverse("groups-list"))
        self.assertEqual(group_list.status_code, 200)
        groups = group_list.json()
        target_group = next(item for item in groups if item["slug"] == self.group.slug)
        self.assertIn("seo", target_group)
        self.assertEqual(target_group["seo"]["h1"], self.group.name)
        self.assertEqual(target_group["seo"]["canonical_url"], f"/groups/{self.group.slug}")

        group_detail = self.client.get(reverse("groups-detail", kwargs={"group_identifier": self.group.slug}))
        self.assertEqual(group_detail.status_code, 200)
        group_detail_data = group_detail.json()
        self.assertIn("seo", group_detail_data["category"])
        self.assertIn("seo", group_detail_data["products"][0])

    def test_product_detail_includes_breadcrumbs_with_types(self):
        parent_group = self.group.__class__.objects.create(name="Каталог раздел", slug="catalog-razdel")
        self.group.parent = parent_group
        self.group.save(update_fields=["parent"])
        self.product.brand.name = "NOVATEH"
        self.product.brand.slug = "novateh"
        self.product.brand.save(update_fields=["name", "slug"])

        response = self.client.get(reverse("products-detail", kwargs={"product_identifier": self.product.slug}))

        self.assertEqual(response.status_code, 200)
        breadcrumbs = response.json()["breadcrumbs"]
        self.assertEqual(
            breadcrumbs,
            [
                {"title": "Каталог", "url": "/catalog", "type": "catalog"},
                {"title": parent_group.name, "url": f"/group/{parent_group.slug}", "type": "category"},
                {"title": self.group.name, "url": f"/group/{self.group.slug}", "type": "subcategory"},
                {"title": self.product.brand.name, "url": f"/brand/{self.product.brand.slug}", "type": "brand"},
                {"title": self.product.name, "url": None, "type": "product"},
            ],
        )
