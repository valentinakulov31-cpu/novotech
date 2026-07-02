from django.conf import settings
from django.http import HttpResponse
from django.test import TestCase
from django.test.client import RequestFactory
from django_prose_editor.widgets import AdminProseEditorWidget
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

    def test_product_admin_uses_prose_editor_for_description(self):
        form = ProductAdminForm()
        self.assertIsInstance(form.fields["description"].widget, AdminProseEditorWidget)

    def test_product_description_sanitizer_strips_images_and_media(self):
        field = ProductAdminForm().fields["description"]
        dirty = (
            '<p><img src="http://example.com/x.png"><strong>жирный</strong></p>'
            '<script>alert(1)</script>'
            '<iframe src="http://example.com"></iframe>'
            '<ul><li>пункт</li></ul>'
        )
        cleaned = field.clean(dirty)
        self.assertNotIn("<img", cleaned)
        self.assertNotIn("<script", cleaned)
        self.assertNotIn("<iframe", cleaned)
        self.assertIn("<strong>жирный</strong>", cleaned)
        self.assertIn("<li>пункт</li>", cleaned)

    def test_product_description_empty_paragraph_saves_as_empty_string(self):
        field = ProductAdminForm().fields["description"]
        self.assertEqual(field.clean("<p></p>"), "")

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

    def test_tinymce_config_registers_table_autoheight_button(self):
        config = settings.TINYMCE_DEFAULT_CONFIG
        self.assertEqual(
            config["external_plugins"]["tableautoheight"],
            '/django-static/shop/js/tinymce-table-autoheight.js',
        )
        self.assertIn('tableautoheight', config["table_toolbar"])

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

    def test_catalog_table_with_single_quoted_attributes_is_recognized(self):
        raw_html = (
            "<table style='border-style: var(--catalog-table-border-style); border-collapse: collapse;' border='1'>"
            "<tbody><tr><td>1</td><td>2</td></tr></tbody></table>"
        )
        cleaned_html = sanitize_catalog_tables(raw_html)
        self.assertIn('data-catalog-table="1"', cleaned_html)
        self.assertIn('padding: 12px', cleaned_html)

    def test_nested_unrecognized_table_is_left_untouched_inside_catalog_table(self):
        raw_html = (
            '<table style="border-style: var(--catalog-table-border-style);" border="1"><tbody>'
            '<tr><td>outer'
            '<table style="width: 50%"><tbody><tr><td>inner</td></tr></tbody></table>'
            '</td><td>2</td></tr></tbody></table>'
        )
        cleaned_html = sanitize_catalog_tables(raw_html)
        self.assertEqual(cleaned_html.count('padding: 12px'), 2)
        self.assertIn('<table style="width: 50%">', cleaned_html)

    def test_catalog_table_sanitizer_is_idempotent(self):
        raw_html = (
            '<table style="border-style: var(--catalog-table-border-style); width: 100.033%;" border="1">'
            '<tbody><tr style="height: 22px;"><td style="width:20%">1</td><td>2</td></tr></tbody></table>'
        )
        once = sanitize_catalog_tables(raw_html)
        self.assertEqual(sanitize_catalog_tables(once), once)

    def test_html_entities_survive_table_normalization(self):
        raw_html = (
            '<p>&nbsp;до</p><table style="border-style: var(--catalog-table-border-style);" border="1">'
            '<tbody><tr><td>x&nbsp;y</td></tr></tbody></table>'
        )
        cleaned_html = sanitize_catalog_tables(raw_html)
        self.assertIn('&nbsp;до', cleaned_html)
        self.assertIn('x&nbsp;y', cleaned_html)

    def test_unbalanced_table_markup_is_left_untouched(self):
        raw_html = '<table style="border-style: solid" border="1"><tr><td>broken'
        self.assertEqual(sanitize_catalog_tables(raw_html), raw_html)
        self.assertIn('border: 1px dotted currentColor', cleaned_html)
        self.assertNotIn('background-color: white', cleaned_html)
        self.assertNotIn('padding: 12px', cleaned_html)
        self.assertNotIn('border="1"', cleaned_html)
