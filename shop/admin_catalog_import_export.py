from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse

from shop.admin_forms import ProductExportForm, ProductImportForm
from shop.admin_inlines import ProductCertificateInline, ProductGalleryItemInline, ProductMediaInline
from shop.admin_mixins import MediaPreviewAdminMixin, TabbedFieldsetsAdminMixin
from shop.admin_support import SEO_FIELD_NAMES
from shop.model_utils import transliterate_slug
from shop.models import Product
from shop.serializers import ProductSerializer
from shop.services import catalog_import as catalog_import_service
from shop.services import media_assets as media_assets_service


class ProductAdminImportExportMixin(TabbedFieldsetsAdminMixin, MediaPreviewAdminMixin, admin.ModelAdmin):
    change_list_template = "admin/shop/product/change_list.html"
    inlines = [ProductMediaInline, ProductGalleryItemInline, ProductCertificateInline]
    list_display = ("id", "name", "sku", "brand", "group", "price", "available", "media_preview")
    search_fields = ("name", "sku", "slug", "search_tsv", "seo_title", "seo_h1")
    autocomplete_fields = ("brand", "group")
    list_filter = ("available", "brand", "group")
    readonly_fields = ("media_preview",)
    fieldsets = (
        ("РћСЃРЅРѕРІРЅРѕРµ", {
            "classes": ("tabbed-fieldset",),
            "fields": (
                "sku",
                "slug",
                "name",
                "price",
                "currency",
                "description",
                "assortment_html",
                "characteristics_html",
                "group",
                "brand",
                "media_preview",
                "available",
                "search_tsv",
            ),
        }),
        ("SEO", {
            "classes": ("tabbed-fieldset",),
            "fields": SEO_FIELD_NAMES,
        }),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "import-xlsx/",
                self.admin_site.admin_view(self.import_xlsx_view),
                name="shop_product_import_xlsx",
            ),
            path(
                "export-xlsx/",
                self.admin_site.admin_view(self.export_xlsx_view),
                name="shop_product_export_xlsx",
            ),
        ]
        return custom_urls + urls

    def import_xlsx_view(self, request):
        if not self.has_add_permission(request):
            raise PermissionDenied("You do not have permission to import products.")

        form = ProductImportForm(request.POST or None, request.FILES or None)

        if request.method == "POST" and form.is_valid():
            try:
                counters, warnings = catalog_import_service.import_products_from_workbook(form.cleaned_data["xlsx_file"])
            except ValidationError as exc:
                form.add_error("xlsx_file", exc)
            else:
                self.message_user(
                    request,
                    (
                        "Import finished. "
                        f"Products created: {counters['products_created']}, "
                        f"updated: {counters['products_updated']}, "
                        f"groups created: {counters['groups_created']}, "
                        f"brands created: {counters['brands_created']}, "
                        f"characteristics created: {counters['characteristics_created']}, "
                        f"product characteristics upserted: {counters['product_characteristics_upserted']}, "
                        f"media imported: {counters['media_items_imported']}, "
                        f"gallery imported: {counters['gallery_items_imported']}, "
                        f"certificates imported: {counters['certificates_imported']}, "
                        f"rows skipped: {counters['rows_skipped']}."
                    ),
                    level=messages.SUCCESS,
                )
                for warning in warnings[:20]:
                    self.message_user(request, warning, level=messages.WARNING)
                if len(warnings) > 20:
                    self.message_user(request, f"Additional warnings not shown: {len(warnings) - 20}.", level=messages.WARNING)
                changelist_url = reverse("admin:shop_product_changelist")
                return HttpResponseRedirect(changelist_url)

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Import products from XLSX",
            "form": form,
            "subtitle": "Upload a spreadsheet with product fields, file/link columns, and char_* columns.",
        }
        return TemplateResponse(request, "admin/shop/product/import_xlsx.html", context)

    def export_xlsx_view(self, request):
        if not self.has_view_or_change_permission(request):
            raise PermissionDenied("You do not have permission to export products.")

        form = ProductExportForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            selected_group = form.cleaned_data["group"]
            if selected_group:
                return self._export_single_group_workbook(selected_group)
            return self._export_grouped_zip()

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Export products to XLSX",
            "form": form,
            "subtitle": "Download a spreadsheet in the same format as the import template. Pick one group for a single XLSX or leave it empty for a ZIP split by groups.",
            "submit_label": "Export",
        }
        return TemplateResponse(request, "admin/shop/product/export_xlsx.html", context)

    def _export_single_group_workbook(self, group):
        headers, rows = catalog_import_service.build_product_export_rows(Product.objects.filter(group=group).order_by("name", "id"))
        payload = catalog_import_service.workbook_bytes_from_headers_and_rows(headers, rows, title=group.slug or group.name)
        filename = f"products_{transliterate_slug(group.slug or group.name)}.xlsx"
        response = HttpResponse(
            payload,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    def _export_grouped_zip(self):
        from shop.models import Group

        buffer = BytesIO()
        with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
            groups = Group.objects.order_by("name")
            for group in groups:
                headers, rows = catalog_import_service.build_product_export_rows(Product.objects.filter(group=group).order_by("name", "id"))
                if not rows:
                    continue
                archive.writestr(
                    f"products_{transliterate_slug(group.slug or group.name)}.xlsx",
                    catalog_import_service.workbook_bytes_from_headers_and_rows(headers, rows, title=group.slug or group.name),
                )

            headers, rows = catalog_import_service.build_product_export_rows(Product.objects.filter(group__isnull=True).order_by("name", "id"))
            if rows:
                archive.writestr(
                    "products_without_group.xlsx",
                    catalog_import_service.workbook_bytes_from_headers_and_rows(headers, rows, title="Without group"),
                )

        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type="application/zip")
        response["Content-Disposition"] = 'attachment; filename="products_by_groups.zip"'
        return response

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        media_assets_service.ensure_single_primary(form.instance)
        media_assets_service.sync_product_media(form.instance)
