from django.urls import reverse

from shop.models import Agent, PUBLISH_STATUS_DRAFT, PUBLISH_STATUS_PUBLISHED, Product
from shop.tests_catalog_support import CatalogApiFixtureBase


class CatalogFacetApiTests(CatalogApiFixtureBase):
    def test_group_filters_return_facets_with_counts(self):
        response = self.client.get(reverse("group-filters", kwargs={"group_id": self.group.id}))
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["count"], 1)
        self.assertEqual(data["price"]["min"], 100.0)
        self.assertEqual(data["price"]["max"], 100.0)
        self.assertEqual(data["brands"][0]["slug"], "energoroll")

        attr_map = {item["slug"]: item for item in data["attributes"]}
        self.assertIn("tolschina-ot-mm", attr_map)
        self.assertEqual(attr_map["tolschina-ot-mm"]["values"][0]["value"], "20")
        self.assertEqual(attr_map["tolschina-ot-mm"]["values"][0]["count"], 1)
        self.assertEqual(attr_map["tolschina-ot-mm"]["range"]["min"], 20.0)

    def test_products_filter_endpoint_filters_by_query_and_attribute(self):
        response = self.client.post(
            reverse("products-filter"),
            {
                "q": "РЎвЂљР ВµР С—Р В»Р С•Р С‘Р В·Р С•Р В»РЎРЏРЎвЂ Р С‘РЎРЏ ENERGOROLL",
                "group_id": self.group.id,
                "attributes": {
                    "tolschina-ot-mm": ["20"],
                    "pokrytie": ["Р В¤Р С•Р В»РЎРЉР С–Р В°"],
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["sku"], "ER-0001")

    def test_products_list_supports_attribute_filters(self):
        response = self.client.get(
            reverse("products-list"),
            {
                "group_id": self.group.id,
                "attr.tolschina-ot-mm": "20",
                "attr.pokrytie": "Р В¤Р С•Р В»РЎРЉР С–Р В°",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["sku"], "ER-0001")

    def test_products_list_supports_popular_random_four(self):
        for index in range(9):
            Product.objects.create(
                sku=f"POP-{index}",
                name=f"Popular {index}",
                price="99.00",
                currency="RUB",
                group=self.group,
                brand=self.brand,
                available=True,
            )

        response = self.client.get(reverse("products-list"), {"popular": "true"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 4)

    def test_catalog_results_endpoint_uses_shared_context_and_filters(self):
        response = self.client.post(
            reverse("catalog-results"),
            {
                "context": {
                    "q": "Р СћР ВµР С—Р В»Р С•Р С‘Р В·Р С•Р В»РЎРЏРЎвЂ Р С‘РЎРЏ ENERGOROLL",
                    "group_slug": "teploizolyatsiya",
                    "brand_slug": "energoroll",
                },
                "filters": {
                    "available": True,
                    "attributes": {
                        "pokrytie": ["Р В¤Р С•Р В»РЎРЉР С–Р В°"],
                    },
                },
                "page": 1,
                "page_size": 12,
                "sort": "relevance",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["pagination"]["count"], 1)
        self.assertEqual(data["results"][0]["sku"], "ER-0001")
        self.assertEqual(data["context"]["group_slug"], "teploizolyatsiya")
        self.assertEqual(data["context"]["brand_slug"], "energoroll")

    def test_catalog_facets_endpoint_returns_group_brand_and_attribute_facets(self):
        response = self.client.post(
            reverse("catalog-facets"),
            {
                "context": {
                    "q": "ENERGOROLL",
                    "brand_slug": "energoroll",
                },
                "filters": {
                    "attributes": {
                        "pokrytie": ["Р В¤Р С•Р В»РЎРЉР С–Р В°"],
                    }
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["summary"]["total_products"], 1)
        self.assertTrue(any(item["slug"] == "energoroll" for item in data["brands"]))
        self.assertTrue(any(item["slug"] == "teploizolyatsiya" for item in data["groups"]))
        attr_map = {item["slug"]: item for item in data["attributes"]}
        self.assertTrue(attr_map["pokrytie"]["values"][0]["selected"])

    def test_agents_endpoint_returns_published_agents_in_order(self):
        Agent.objects.create(
            full_name="Draft Agent",
            position="Hidden",
            email="draft@example.com",
            phone="+70000000000",
            sort_order=0,
            status=PUBLISH_STATUS_DRAFT,
        )
        Agent.objects.create(
            full_name="Second Agent",
            position="Sales specialist",
            email="second@example.com",
            phone="+79095338586",
            sort_order=2,
            status=PUBLISH_STATUS_PUBLISHED,
        )
        Agent.objects.create(
            full_name="First Agent",
            position="Client manager",
            email="first@example.com",
            phone="+79612283100",
            sort_order=1,
            status=PUBLISH_STATUS_PUBLISHED,
        )

        response = self.client.get(reverse("agents-list"))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual([item["full_name"] for item in data], ["First Agent", "Second Agent"])
        self.assertEqual(data[0]["position"], "Client manager")
        self.assertEqual(data[0]["email"], "first@example.com")
        self.assertEqual(data[0]["phone"], "+79612283100")
