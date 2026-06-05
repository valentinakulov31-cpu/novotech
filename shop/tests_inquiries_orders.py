from decimal import Decimal

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from shop.models import Brand, Group, Inquiry, OrderEmailRecipient, OrderEmailSettings, PUBLISH_STATUS_PUBLISHED, Product, PublicOrder


class InquiryApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_inquiry_endpoint_creates_record(self):
        response = self.client.post(
            reverse("inquiry-create"),
            {
                "name": "РРІР°РЅ",
                "phone": "+79990001122",
                "email": "ivan@example.com",
                "message": "РќСѓР¶РЅР° РєРѕРЅСЃСѓР»СЊС‚Р°С†РёСЏ РїРѕ С‚РѕРІР°СЂСѓ",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["name"], "РРІР°РЅ")
        self.assertEqual(Inquiry.objects.count(), 1)
        inquiry = Inquiry.objects.first()
        self.assertEqual(inquiry.phone, "+79990001122")

    def test_inquiry_endpoint_requires_phone_or_email(self):
        response = self.client.post(
            reverse("inquiry-create"),
            {
                "name": "????????",
                "message": "?????????????????????? ?????? ????????????",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("non_field_errors", response.json())


class PublicOrderApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.group = Group.objects.create(name="РўРµРїР»РѕРёР·РѕР»СЏС†РёСЏ", slug="teploizolyatsiya")
        self.brand = Brand.objects.create(name="ENERGOROLL", slug="energoroll")
        self.product_one = Product.objects.create(
            sku="ER-0001",
            name="Р¦РёР»РёРЅРґСЂС‹ ENERGOROLL RK",
            price=Decimal("100.00"),
            currency="RUB",
            group=self.group,
            brand=self.brand,
            available=True,
        )
        self.product_two = Product.objects.create(
            sku="ER-0002",
            name="РњР°С‚С‹ ENERGOROLL",
            price=Decimal("200.00"),
            currency="RUB",
            group=self.group,
            brand=self.brand,
            available=True,
        )

    def test_public_order_endpoint_creates_order_with_items(self):
        response = self.client.post(
            reverse("public-order-create"),
            {
                "name": "РРІР°РЅ",
                "phone": "+79990001122",
                "email": "ivan@example.com",
                "address": "РљСЂР°СЃРЅРѕСЏСЂСЃРє, СѓР». РўРµСЃС‚РѕРІР°СЏ, 1",
                "comment": "РџРѕР·РІРѕРЅРёС‚Рµ РїРµСЂРµРґ РґРѕСЃС‚Р°РІРєРѕР№",
                "items": [
                    {"product_id": self.product_one.id, "qty": 2},
                    {"product_id": self.product_two.id, "qty": 1},
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["name"], "РРІР°РЅ")
        self.assertEqual(data["total_items"], 3)
        self.assertEqual(len(data["items"]), 2)
        self.assertEqual(PublicOrder.objects.count(), 1)
        order = PublicOrder.objects.get()
        self.assertEqual(order.address, "РљСЂР°СЃРЅРѕСЏСЂСЃРє, СѓР». РўРµСЃС‚РѕРІР°СЏ, 1")
        self.assertEqual(order.items.count(), 2)

    def test_public_order_requires_phone_and_items(self):
        response = self.client.post(
            reverse("public-order-create"),
            {
                "name": "РџРµС‚СЂ",
                "items": [],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("phone", data)


@override_settings(
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class PublicOrderEmailTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        mail.outbox = []
        self.group = Group.objects.create(name="РўРµРїР»РѕРёР·РѕР»СЏС†РёСЏ", slug="teploizolyatsiya-email")
        self.brand = Brand.objects.create(name="ENERGOROLL", slug="energoroll-email")
        self.product = Product.objects.create(
            sku="EMAIL-1",
            name="Р¦РёР»РёРЅРґСЂС‹ ENERGOROLL RK",
            price=Decimal("100.00"),
            currency="RUB",
            group=self.group,
            brand=self.brand,
            available=True,
        )
        self.recipient = OrderEmailRecipient.objects.create(email="sales@example.com", name="Sales", is_active=True)
        self.email_settings = OrderEmailSettings.objects.create(
            title="Order notifications",
            notification_type="order",
            subject="Р—Р°РєР°Р· СЃ С„СЂРѕРЅС‚Р°",
            intro_html="<p>РќРѕРІС‹Р№ Р·Р°РєР°Р· РЅР° СЃР°Р№С‚Рµ.</p>",
            footer_html="<p>РџСЂРѕРІРµСЂСЊС‚Рµ Р·Р°СЏРІРєСѓ РІ Р°РґРјРёРЅРєРµ.</p>",
            status=PUBLISH_STATUS_PUBLISHED,
        )

    def test_public_order_sends_email_to_active_recipients(self):
        response = self.client.post(
            reverse("public-order-create"),
            {
                "name": "РРІР°РЅ",
                "phone": "+79990001122",
                "email": "ivan@example.com",
                "address": "РљСЂР°СЃРЅРѕСЏСЂСЃРє, СѓР». РўРµСЃС‚РѕРІР°СЏ, 1",
                "comment": "РџРѕР·РІРѕРЅРёС‚Рµ РїРµСЂРµРґ РґРѕСЃС‚Р°РІРєРѕР№",
                "items": [{"product_id": self.product.id, "qty": 2}],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["sales@example.com"])
        self.assertEqual(mail.outbox[0].subject, "Р—Р°РєР°Р· СЃ С„СЂРѕРЅС‚Р°")
        self.assertIn("\u041d\u041e\u0412\u0410\u0422\u0415\u0425", mail.outbox[0].body)
        self.assertTrue(mail.outbox[0].alternatives)
        html_body = mail.outbox[0].alternatives[0][0]
        self.assertIn("<!DOCTYPE html>", html_body)
        self.assertIn("background:#ffd400", html_body)
        self.assertIn("НОВАТЕХ", html_body)

    def test_public_order_skips_email_without_active_recipients(self):
        self.recipient.is_active = False
        self.recipient.save(update_fields=["is_active"])

        response = self.client.post(
            reverse("public-order-create"),
            {
                "name": "РџРµС‚СЂ",
                "phone": "+79990001111",
                "items": [{"product_id": self.product.id, "qty": 1}],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 0)
