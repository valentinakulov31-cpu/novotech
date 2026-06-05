from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from shop.models import ContactInfo, HtmlContent, News, NewsAttachment, PUBLISH_STATUS_DRAFT, PUBLISH_STATUS_PUBLISHED, Sert, Slider


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class SliderApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        Slider.objects.create(
            image="/static/slider-2.jpg",
            title="Second",
            text="Second text",
            slug="second",
            sort_order=2,
            status=PUBLISH_STATUS_PUBLISHED,
        )
        Slider.objects.create(
            image="/static/slider-1.jpg",
            title="First",
            text="First text",
            slug="first",
            sort_order=1,
            status=PUBLISH_STATUS_PUBLISHED,
        )
        Slider.objects.create(
            image="/static/slider-hidden.jpg",
            title="Hidden",
            text="Hidden text",
            slug="hidden",
            sort_order=0,
            status=PUBLISH_STATUS_DRAFT,
        )
        Slider.objects.create(
            image="/static/slider-no-slug.jpg",
            title="No slug",
            text="No slug text",
            sort_order=3,
            status=PUBLISH_STATUS_PUBLISHED,
        )

    def test_slider_endpoint_returns_active_items_as_array_in_order(self):
        response = self.client.get(reverse("slider-list"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual([item["slug"] for item in data], ["first", "second", None])
        self.assertNotIn("hidden", [item["slug"] for item in data])


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class NewsAndSertApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.news = News.objects.create(
            title="РќРѕРІР°СЏ РїРѕСЃС‚Р°РІРєР°",
            slug="novaya-postavka",
            content="РџСЂРёРµС…Р°Р»Р° РЅРѕРІР°СЏ РїР°СЂС‚РёСЏ С‚РѕРІР°СЂРѕРІ",
            status=PUBLISH_STATUS_PUBLISHED,
        )
        NewsAttachment.objects.create(
            news=self.news,
            title="РљР°С‚Р°Р»РѕРі PDF",
            storage_path="media/news-catalog.pdf",
            url="/static/news-catalog.pdf",
            mime_type="application/pdf",
            size_bytes=100,
            sort_order=1,
        )
        NewsAttachment.objects.create(
            news=self.news,
            title="Р’РёРґРµРѕ РѕР±Р·РѕСЂ",
            storage_path="media/news-video.mp4",
            url="/static/news-video.mp4",
            mime_type="video/mp4",
            size_bytes=500,
            sort_order=2,
        )
        News.objects.create(
            title="Draft news",
            slug="draft-news",
            content="Draft body",
            status=PUBLISH_STATUS_DRAFT,
        )
        Sert.objects.create(
            title="РЎРµСЂС‚РёС„РёРєР°С‚ ISO",
            storage_path="media/iso.pdf",
            url="/static/iso.pdf",
            mime_type="application/pdf",
            size_bytes=200,
            sort_order=1,
            status=PUBLISH_STATUS_PUBLISHED,
        )
        Sert.objects.create(
            title="Draft sert",
            storage_path="media/draft.pdf",
            url="/static/draft.pdf",
            mime_type="application/pdf",
            size_bytes=50,
            sort_order=2,
            status=PUBLISH_STATUS_DRAFT,
        )

    def test_news_endpoint_returns_attachments(self):
        response = self.client.get(reverse("news-list"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(len(data[0]["attachments"]), 2)
        self.assertEqual(data[0]["attachments"][1]["file_kind"], "video")
        self.assertNotIn("storage_path", data[0]["attachments"][0])

    def test_sert_endpoint_returns_active_files(self):
        response = self.client.get(reverse("sert-list"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["url"], "/static/iso.pdf")
        self.assertEqual(data[0]["file_kind"], "document")
        self.assertNotIn("storage_path", data[0])


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class ContentApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        HtmlContent.objects.create(
            title="Draft HTML",
            html_first="<p>Draft first</p>",
            html_second="<p>Draft second</p>",
            status=PUBLISH_STATUS_DRAFT,
        )
        ContactInfo.objects.create(
            title="Draft contacts",
            full_name="Draft manager",
            address="Draft address",
            schedule="Draft schedule",
            phone="+70000000000",
            email="draft@example.com",
            status=PUBLISH_STATUS_DRAFT,
        )
        HtmlContent.objects.create(
            title="Р“Р»Р°РІРЅС‹Р№ HTML",
            html_first="<section><h1>РџРµСЂРІС‹Р№ Р±Р»РѕРє</h1></section>",
            html_second="<section><p>Р’С‚РѕСЂРѕР№ Р±Р»РѕРє</p></section>",
            status=PUBLISH_STATUS_PUBLISHED,
        )
        ContactInfo.objects.create(
            title="РќРђРЁР РљРћРќРўРђРљРўР«",
            address="630007, Рі. РќРѕРІРѕСЃРёР±РёСЂСЃРє,\nРїРµСЂ. РџСЂРёСЃС‚Р°РЅСЃРєРёР№, 2",
            latitude=Decimal("55.014575"),
            longitude=Decimal("82.938639"),
            schedule="РџРќ-Р§Рў: СЃ 9.00 РґРѕ 18.00\nРџРў: СЃ 9.00 РґРѕ 17.00",
            phone="+7 (383) 263-20-99",
            email="nskteplo-sib.ru",
            status=PUBLISH_STATUS_PUBLISHED,
        )

    def test_html_content_endpoint_returns_two_html_strings(self):
        response = self.client.get(reverse("html-content"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertNotIn("Draft first", data["html_first"])
        self.assertEqual(data["html_first"], "<section><h1>РџРµСЂРІС‹Р№ Р±Р»РѕРє</h1></section>")
        self.assertEqual(data["html_second"], "<section><p>Р’С‚РѕСЂРѕР№ Р±Р»РѕРє</p></section>")

    def test_contact_info_endpoint_returns_contacts(self):
        response = self.client.get(reverse("contact-info"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertNotIn("id", data)
        self.assertNotIn("updated_at", data)
        self.assertEqual(data["title"], "РќРђРЁР РљРћРќРўРђРљРўР«")
        self.assertEqual(data["phone"], "+7 (383) 263-20-99")
        self.assertEqual(data["latitude"], "55.014575")
        self.assertEqual(data["longitude"], "82.938639")
        self.assertIn("РќРѕРІРѕСЃРёР±РёСЂСЃРє", data["address"])
