from io import BytesIO
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from shop.company_documents import validate_company_document
from shop.catalog_payload_builders import build_brand_grouped_products_payload
from shop.models import Brand, Group, Product, HtmlContent, PUBLISH_STATUS_PUBLISHED
from shop.serializers_content import HtmlContentSerializer
from shop.admin_content_forms import HtmlContentAdminForm, SliderAdminForm
from shop.sitemaps import StaticPagesSitemap


class ChecklistReleaseTests(TestCase):
    def test_brand_group_order_is_explicit_and_uncategorized_last(self):
        brand = Brand.objects.create(name="Ordering", slug="ordering")
        accessories = Group.objects.create(name="Accessories", slug="acc", sort_order=1000)
        main = Group.objects.create(name="Main", slug="main", sort_order=-1)
        for index, group in enumerate([accessories, None, main]):
            Product.objects.create(sku=f"test-{index}", name=f"Item {index}", brand=brand, group=group, price=1)
        payload = build_brand_grouped_products_payload(brand)
        self.assertEqual([row["id"] for row in payload["categories"]], [main.pk, accessories.pk, None])

    def test_accepts_document_formats_and_rejects_disguised_files(self):
        docx = BytesIO()
        with ZipFile(docx, "w") as archive:
            archive.writestr("[Content_Types].xml", "<Types/>")
            archive.writestr("word/document.xml", "<document/>")
        for name, data in [("test.pdf", b"%PDF-1.7\n"), ("test.doc", bytes.fromhex("d0cf11e0a1b11ae1")), ("test.docx", docx.getvalue())]:
            upload = SimpleUploadedFile(name, data)
            validate_company_document(upload)
            self.assertEqual(upload.tell(), 0)
        for name, data in [("test.html", b"<script>bad</script>"), ("test.pdf", b"<html>bad</html>"), ("test.docx", b"not zip"), ("test.pdf", b"%PDF-" + b"x" * (10 * 1024 * 1024))]:
            with self.assertRaises(ValidationError):
                validate_company_document(SimpleUploadedFile(name, data))

    def test_document_upload_survives_save_and_is_exposed_by_api(self):
        with TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            form = HtmlContentAdminForm(data={"title": "Details", "html_first": "<p>Office</p>", "html_second": "<p>Details</p>", "status": PUBLISH_STATUS_PUBLISHED, "requisites_file_title": "Download"}, files={"requisites_file": SimpleUploadedFile("details.pdf", b"%PDF-1.7\n")})
            form.data = {**form.data, "created_at": timezone.now()}
            self.assertTrue(form.is_valid(), form.errors)
            content = form.save()
            self.assertTrue(content.requisites_file.storage.exists(content.requisites_file.name))
            payload = HtmlContentSerializer(content).data
            self.assertTrue(payload["requisites_file"].startswith("/static/company_documents/"))
            self.assertEqual(payload["requisites_file_title"], "Download")
            self.assertEqual(payload["html_second"], "<p>Details</p>")

    def test_empty_document_is_backwards_compatible(self):
        payload = HtmlContentSerializer(HtmlContent(html_first="a", html_second="b")).data
        self.assertIsNone(payload["requisites_file"])

    def test_retired_certificate_page_is_not_in_sitemap(self):
        self.assertNotIn("/certificates", [row["location"] for row in StaticPagesSitemap().items()])

    def test_banner_editor_supports_safe_formatting(self):
        field = SliderAdminForm().fields["text"]
        html = field.clean('<p>Some <strong>bold</strong><script>alert(1)</script></p>')
        self.assertIn("<strong>bold</strong>", html)
        self.assertNotIn("<script", html)
