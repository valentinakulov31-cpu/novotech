from decimal import Decimal
from pathlib import Path
import shutil
import tempfile

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.test.client import RequestFactory
from django.urls import reverse

from shop.admin import ContactInfoAdmin, HtmlContentAdmin, MediaLibraryAdmin, collect_media_library_assets, delete_media_asset
from shop.models import Brand, ContactInfo, HtmlContent, MediaLibrary, News, Product, ProductMedia, PUBLISH_STATUS_DRAFT
from shop.tests_support import TEST_GIF


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class AdminPublishWorkflowTests(TestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_superuser(
            username="workflow-admin",
            email="workflow-admin@example.com",
            password="secret123",
        )
        self.site = AdminSite()

    def test_html_content_preview_is_available_for_draft_content(self):
        content = HtmlContent.objects.create(
            title="Draft HTML preview",
            html_first="<p>Draft first</p>",
            html_second="<p>Draft second</p>",
            status=PUBLISH_STATUS_DRAFT,
        )
        admin_instance = HtmlContentAdmin(HtmlContent, self.site)
        request = RequestFactory().get(reverse("admin:shop_htmlcontent_preview", args=[content.pk]))
        request.user = self.admin_user

        response = admin_instance.preview_view(request, str(content.pk))

        self.assertEqual(response.status_code, 200)
        rendered = response.rendered_content
        self.assertIn("Draft HTML preview", rendered)
        self.assertIn("Draft first", rendered)

    def test_contact_info_preview_is_available_for_draft_content(self):
        contact = ContactInfo.objects.create(
            title="Draft contacts",
            full_name="Draft manager",
            address="Draft address",
            schedule="Draft schedule",
            phone="+70000000000",
            email="draft@example.com",
            status=PUBLISH_STATUS_DRAFT,
        )
        admin_instance = ContactInfoAdmin(ContactInfo, self.site)
        request = RequestFactory().get(reverse("admin:shop_contactinfo_preview", args=[contact.pk]))
        request.user = self.admin_user

        response = admin_instance.preview_view(request, str(contact.pk))

        self.assertEqual(response.status_code, 200)
        rendered = response.rendered_content
        self.assertIn("Draft contacts", rendered)
        self.assertIn("Draft manager", rendered)


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class MediaLibraryAdminTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media_root)
        self.override.enable()
        self.site = AdminSite()
        self.admin = MediaLibraryAdmin(MediaLibrary, self.site)
        self.product = Product.objects.create(
            sku="MEDIA-1",
            name="Media product",
            price=Decimal("100.00"),
            currency="RUB",
            available=True,
        )
        self.brand = Brand.objects.create(name="Media brand", slug="media-brand", media="/static/admin_uploads/brands/shared.jpg")
        self.news = News.objects.create(title="Media news", slug="media-news", content="Body", media=["/static/admin_uploads/brands/shared.jpg"])
        self.shared_storage_path = Path(self.media_root) / "admin_uploads" / "brands" / "shared.jpg"
        self.shared_storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.shared_storage_path.write_bytes(TEST_GIF)
        ProductMedia.objects.create(
            product=self.product,
            storage_path=str(self.shared_storage_path),
            url="/static/admin_uploads/brands/shared.jpg",
            mime_type="image/jpeg",
            media_kind="image",
            size_bytes=len(TEST_GIF),
            is_primary=True,
            sort_order=0,
        )

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def test_collect_media_library_assets_groups_shared_usages(self):
        assets = collect_media_library_assets()
        shared_asset = next(item for item in assets if item["url"] == "/static/admin_uploads/brands/shared.jpg")
        self.assertEqual(shared_asset["usage_count"], 3)
        self.assertEqual(shared_asset["kind"], "image")
        self.assertTrue(shared_asset["file_exists"])
        usage_sources = {usage["source_label"] for usage in shared_asset["usages"]}
        self.assertIn("Brand image", usage_sources)
        self.assertIn("News media field", usage_sources)
        self.assertIn("Product media", usage_sources)

    def test_delete_media_asset_removes_file_and_all_dependencies(self):
        result = delete_media_asset(
            asset_url="/static/admin_uploads/brands/shared.jpg",
            asset_storage_path=str(self.shared_storage_path),
        )

        self.brand.refresh_from_db()
        self.news.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(self.brand.media, None)
        self.assertIsNone(self.news.media)
        self.assertIsNone(self.product.media)
        self.assertEqual(ProductMedia.objects.count(), 0)
        self.assertFalse(self.shared_storage_path.exists())
        self.assertEqual(result["deleted_rows"]["product_media"], 1)
        self.assertEqual(result["cleared_fields"]["brands"], 1)
        self.assertEqual(result["updated_news"], 1)
        self.assertTrue(result["file_deleted"])

    def test_media_library_admin_changelist_renders_custom_table(self):
        request = RequestFactory().get(reverse("admin:shop_medialibrary_changelist"))
        request.user = get_user_model().objects.create_superuser(
            username="media-admin",
            email="media-admin@example.com",
            password="secret123",
        )

        response = self.admin.changelist_view(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Media library", response.rendered_content)
        self.assertIn("Delete everywhere", response.rendered_content)
