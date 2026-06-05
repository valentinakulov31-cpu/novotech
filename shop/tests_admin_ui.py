from django.conf import settings
from django.http import HttpResponse
from django.test import TestCase
from django.test.client import RequestFactory
from tinymce.widgets import TinyMCE

from django_shop.middleware import MediaEmbedHeadersMiddleware
from shop.admin import HtmlContentAdminForm, NewsAdminForm, OrderEmailSettingsAdminForm, ProductAdminForm, sanitize_catalog_tables


class MediaEmbedHeadersMiddlewareTests(TestCase):
    def test_allows_iframe_for_target_pdf_paths_only(self):
        factory = RequestFactory()
        middleware = MediaEmbedHeadersMiddleware(lambda request: HttpResponse("ok"))

        allowed_response = middleware(factory.get("/static/admin_uploads/serts/test.pdf"))
        self.assertNotIn("X-Frame-Options", allowed_response)
        self.assertEqual(allowed_response["Cross-Origin-Opener-Policy"], "unsafe-none")
        self.assertEqual(allowed_response["Content-Security-Policy"], "frame-ancestors *")

        blocked_response = middleware(factory.get("/static/admin_uploads/slider/test.jpg"))
        self.assertNotIn("Cross-Origin-Opener-Policy", blocked_response)


class RichTextAdminFormTests(TestCase):
    def test_html_content_admin_uses_tinymce_widgets(self):
        form = HtmlContentAdminForm()
        self.assertIsInstance(form.fields["html_first"].widget, TinyMCE)
        self.assertIsInstance(form.fields["html_second"].widget, TinyMCE)

    def test_news_admin_uses_tinymce_widget_for_content(self):
        form = NewsAdminForm()
        self.assertIsInstance(form.fields["content"].widget, TinyMCE)

    def test_product_admin_uses_tinymce_widget_for_assortment_html(self):
        form = ProductAdminForm()
        self.assertIsInstance(form.fields["assortment_html"].widget, TinyMCE)

    def test_product_admin_uses_tinymce_widget_for_characteristics_html(self):
        form = ProductAdminForm()
        self.assertIsInstance(form.fields["characteristics_html"].widget, TinyMCE)

    def test_order_email_settings_admin_uses_tinymce_widgets(self):
        form = OrderEmailSettingsAdminForm()
        self.assertIsInstance(form.fields["intro_html"].widget, TinyMCE)
        self.assertIsInstance(form.fields["footer_html"].widget, TinyMCE)

    def test_tinymce_default_config_exposes_catalog_table_style(self):
        config = settings.TINYMCE_DEFAULT_CONFIG
        self.assertIn('/django-static/shop/css/tinymce-content.css', config["content_css"])
        self.assertTrue(any(
            item.get("value") == "var(--catalog-table-border-style)"
            for item in config["table_border_styles"]
        ))
        self.assertEqual(config["table_class_list"], [])
        self.assertEqual(config["style_formats"], [])
        self.assertTrue(config["table_appearance_options"])
        self.assertTrue(config["table_advtab"])
        self.assertNotIn('tableclass', config["toolbar"])

    def test_catalog_table_sanitizer_enforces_catalog_design_inline(self):
        raw_html = (
            '<ul><li>Text<table style="border-style: var(--catalog-table-border-style); border-collapse: collapse; width: 100.033%; '
            'border-width: 1px; height: 44px;" border="1"><tbody>'
            '<tr style="height: 22px;"><td style="width:20%">1</td><td style="width:20%">2</td></tr>'
            '</tbody></table></li></ul>'
        )
        cleaned_html = sanitize_catalog_tables(raw_html)
        self.assertIn('border-style: var(--catalog-table-border-style)', cleaned_html)
        self.assertIn('data-catalog-table="1"', cleaned_html)
        self.assertNotIn('class="catalog-table"', cleaned_html)
        self.assertIn('width: 100%', cleaned_html)
        self.assertIn('background-color: white', cleaned_html)
        self.assertIn('font-size: 14px', cleaned_html)
        self.assertNotIn('border="1"', cleaned_html)
        self.assertIn('padding: 12px', cleaned_html)
        self.assertIn('border: 1px solid #e1e1e1', cleaned_html)
        self.assertIn('text-align: left', cleaned_html)
        self.assertIn('text-align: center', cleaned_html)
        self.assertIn('width: 20%', cleaned_html)

    def test_catalog_table_sanitizer_can_switch_back_to_regular_border_styles(self):
        raw_html = (
            '<table data-catalog-table="1" style="border-style: solid; width: 100%; background-color: white; '
            'border-collapse: collapse; font-size: 14px"><tbody>'
            '<tr><td style="padding: 12px; border: 1px solid #e1e1e1; text-align: left; width: 20%">1</td>'
            '<td style="padding: 12px; border: 1px solid #e1e1e1; text-align: center; width: 20%">2</td></tr>'
            '</tbody></table>'
        )
        cleaned_html = sanitize_catalog_tables(raw_html)
        self.assertNotIn('data-catalog-table="1"', cleaned_html)
        self.assertIn('border-style: solid', cleaned_html)
        self.assertIn('border-width: 1px', cleaned_html)
        self.assertNotIn('background-color: white', cleaned_html)
        self.assertNotIn('font-size: 14px', cleaned_html)
        self.assertNotIn('padding: 12px', cleaned_html)
        self.assertNotIn('text-align: left', cleaned_html)
        self.assertNotIn('text-align: center', cleaned_html)
        self.assertIn('border: 1px solid currentColor', cleaned_html)
        self.assertIn('width: 20%', cleaned_html)

    def test_catalog_table_sanitizer_removes_custom_design_when_marker_is_gone(self):
        raw_html = (
            '<table data-catalog-table="1" style="width: 100%; background-color: white; '
            'border-collapse: collapse; font-size: 14px; border-width: 1px"><tbody>'
            '<tr><td style="padding: 12px; border: 1px solid #e1e1e1; text-align: left; width: 20%">1</td>'
            '<td style="padding: 12px; border: 1px solid #e1e1e1; text-align: center; width: 20%">2</td></tr>'
            '</tbody></table>'
        )
        cleaned_html = sanitize_catalog_tables(raw_html)
        self.assertNotIn('data-catalog-table="1"', cleaned_html)
        self.assertNotIn('background-color: white', cleaned_html)
        self.assertIn('border-collapse: collapse', cleaned_html)
        self.assertNotIn('font-size: 14px', cleaned_html)
        self.assertNotIn('padding: 12px', cleaned_html)
        self.assertNotIn('border: 1px solid #e1e1e1', cleaned_html)
        self.assertNotIn('text-align: left', cleaned_html)
        self.assertNotIn('text-align: center', cleaned_html)
        self.assertIn('border-width: 1px', cleaned_html)
        self.assertIn('width: 20%', cleaned_html)

    def test_signature_only_table_is_not_forced_into_catalog_design(self):
        raw_html = (
            '<table style="width: 100%; background-color: white; border-collapse: collapse; '
            'font-size: 14px; border-width: 1px" border="1"><tbody>'
            '<tr><td>1</td><td>2</td></tr></tbody></table>'
        )
        cleaned_html = sanitize_catalog_tables(raw_html)
        self.assertEqual(cleaned_html, raw_html)

    def test_regular_border_styles_are_pushed_to_cells_for_frontend_rendering(self):
        raw_html = (
            '<table style="border-collapse: collapse; width: 100.033%; border-width: 1px; border-style: dotted;" border="1">'
            '<tbody><tr><td>1</td><td>2</td></tr></tbody></table>'
        )
        cleaned_html = sanitize_catalog_tables(raw_html)
        self.assertIn('border-style: dotted', cleaned_html)
        self.assertIn('border-width: 1px', cleaned_html)
        self.assertIn('border-collapse: collapse', cleaned_html)
        self.assertIn('border: 1px dotted currentColor', cleaned_html)
        self.assertNotIn('background-color: white', cleaned_html)
        self.assertNotIn('padding: 12px', cleaned_html)
        self.assertNotIn('border="1"', cleaned_html)
