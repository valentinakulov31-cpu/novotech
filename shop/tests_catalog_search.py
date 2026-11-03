from django.urls import reverse

from shop.tests_catalog_support import CatalogApiFixtureBase


class CatalogSearchApiTests(CatalogApiFixtureBase):
    def test_global_search_uses_characteristics_html(self):
        self.product.characteristics_html = (
            "<table><tr>"
            "<td>Теплопроводность, λ10</td>"
            "<td>Вт/м·°С</td>"
            "<td>0,034</td>"
            "<td>0,034</td>"
            "<td>0,036</td>"
            "<td>ГОСТ 31925-2011</td>"
            "</tr></table>"
        )
        self.product.save(update_fields=["characteristics_html"])

        response = self.client.get(reverse("global-search"), {"q": "Теплопроводность 0,034"})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(any(item["sku"] == "ER-0001" for item in data["results"]["products"]))

    def test_global_search_tolerates_common_russian_typos_in_characteristics_html(self):
        self.product.characteristics_html = (
            "<table><tr>"
            "<td>\u0412\u043e\u0434\u043e\u043f\u043e\u0433\u043b\u043e\u0449\u0435\u043d\u0438\u0435 "
            "\u043f\u043e \u043e\u0431\u044a\u0435\u043c\u0443</td>"
            "<td>1,5%</td>"
            "</tr></table>"
        )
        self.product.save(update_fields=["characteristics_html"])

        response = self.client.get(
            reverse("global-search"),
            {"q": "\u0412\u043e\u0434\u0430\u043f\u043e\u0433\u043b\u0430\u0449\u0435\u043d\u0438\u0435"},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(any(item["sku"] == "ER-0001" for item in data["results"]["products"]))

    def test_catalog_search_uses_characteristics_html(self):
        self.product.characteristics_html = (
            "<table><tr>"
            "<td>Теплопроводность, λ10</td>"
            "<td>Вт/м·°С</td>"
            "<td>0,034</td>"
            "<td>0,034</td>"
            "<td>0,036</td>"
            "<td>ГОСТ 31925-2011</td>"
            "</tr></table>"
        )
        self.product.save(update_fields=["characteristics_html"])

        response = self.client.post(
            reverse("catalog-results"),
            {
                "context": {"q": "теплопроводность гост"},
                "filters": {},
                "page": 1,
                "page_size": 12,
                "sort": "relevance",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(any(item["sku"] == "ER-0001" for item in data["results"]))

    def test_catalog_results_endpoint_supports_typo_tolerant_search(self):
        response = self.client.post(
            reverse("catalog-results"),
            {
                "context": {
                    "q": "ENERGORLL",
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
        self.assertTrue(any(item["sku"] == "ER-0001" for item in data["results"]))

    def test_catalog_results_endpoint_uses_search_tsv_synonyms(self):
        self.product.search_tsv = "insulation, heat"
        self.product.save(update_fields=["search_tsv"])

        response = self.client.post(
            reverse("catalog-results"),
            {
                "context": {
                    "q": "insulation",
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
        self.assertTrue(any(item["sku"] == "ER-0001" for item in data["results"]))
