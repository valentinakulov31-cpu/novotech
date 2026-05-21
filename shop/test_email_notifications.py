from decimal import Decimal

from django.conf import settings
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from tinymce.widgets import TinyMCE

from shop.admin import OrderEmailSettingsAdminForm
from shop.models import (
    Brand,
    Group,
    OrderEmailRecipient,
    OrderEmailSettings,
    PUBLISH_STATUS_PUBLISHED,
    Product,
)


class OrderEmailSettingsAdminFormTests(TestCase):
    def test_form_uses_tinymce_and_has_no_from_email_field(self):
        form = OrderEmailSettingsAdminForm()
        self.assertIsInstance(form.fields["intro_html"].widget, TinyMCE)
        self.assertIsInstance(form.fields["footer_html"].widget, TinyMCE)
        self.assertIn("notification_type", form.fields)
        self.assertNotIn("from_email", form.fields)


@override_settings(
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class PublicOrderEmailNotificationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        mail.outbox = []
        self.group = Group.objects.create(name="Теплоизоляция", slug="teploizolyatsiya-email")
        self.brand = Brand.objects.create(name="ENERGOROLL", slug="energoroll-email")
        self.product = Product.objects.create(
            sku="EMAIL-1",
            name="Цилиндры ENERGOROLL RK",
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
            subject="Заказ с фронта",
            intro_html="<p>Новый заказ на сайте.</p>",
            footer_html="<p>Проверьте заявку в админке.</p>",
            status=PUBLISH_STATUS_PUBLISHED,
        )

    def test_public_order_sends_styled_email(self):
        response = self.client.post(
            reverse("public-order-create"),
            {
                "name": "Иван",
                "phone": "+79990001122",
                "email": "ivan@example.com",
                "address": "Красноярск, ул. Тестовая, 1",
                "comment": "Позвоните перед доставкой",
                "items": [{"product_id": self.product.id, "qty": 2}],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["sales@example.com"])
        self.assertEqual(mail.outbox[0].from_email, settings.DEFAULT_FROM_EMAIL)
        self.assertEqual(mail.outbox[0].subject, "Заказ с фронта")
        self.assertIn("EMAIL-1", mail.outbox[0].body)
        self.assertIn("Иван", mail.outbox[0].body)
        self.assertIn("НОВАТЕХ", mail.outbox[0].alternatives[0][0])


@override_settings(
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="notify@nvt24.ru",
)
class InquiryEmailNotificationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        mail.outbox = []
        self.recipient = OrderEmailRecipient.objects.create(email="office@example.com", name="Office", is_active=True)
        self.email_settings = OrderEmailSettings.objects.create(
            title="Inquiry notifications",
            notification_type="inquiry",
            subject="Новая заявка с сайта #{{inquiry_id}}",
            intro_html="<p>На сайте появилась новая заявка.</p>",
            footer_html="<p>Свяжитесь с клиентом в ближайшее время.</p>",
            status=PUBLISH_STATUS_PUBLISHED,
        )

    def test_inquiry_sends_styled_email(self):
        response = self.client.post(
            reverse("inquiry-create"),
            {
                "name": "Марина",
                "phone": "+79991112233",
                "email": "marina@example.com",
                "message": "Нужна консультация по утеплителю.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["office@example.com"])
        self.assertEqual(mail.outbox[0].from_email, "notify@nvt24.ru")
        self.assertEqual(mail.outbox[0].subject, "Новая заявка с сайта #1")
        self.assertIn("Марина", mail.outbox[0].body)
        self.assertIn("НОВАТЕХ", mail.outbox[0].alternatives[0][0])
