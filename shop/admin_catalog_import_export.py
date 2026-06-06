from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone

from shop.admin_forms import ProductExportForm, ProductImportForm
from shop.admin_inlines import ProductCertificateInline, ProductGalleryItemInline, ProductMediaInline
from shop.admin_mixins import MediaPreviewAdminMixin, TabbedFieldsetsAdminMixin
from shop.admin_support import SEO_FIELD_NAMES
from shop.model_utils import transliterate_slug
from shop.models import Product
from shop.services import catalog_import as catalog_import_service
from shop.services import media_assets as media_assets_service


class ProductAdminImportExportMixin(TabbedFieldsetsAdminMixin, MediaPreviewAdminMixin, admin.ModelAdmin):
    change_list_template = "admin/shop/product/change_list.html"
    inlines = [ProductMediaInline, ProductGalleryItemInline, ProductCertificateInline]
    list_display = ("id", "name", "sku", "brand", "group", "shared_gallery", "price", "available", "media_preview")
    search_fields = ("name", "sku", "slug", "search_tsv", "seo_title", "seo_h1")
    autocomplete_fields = ("brand", "group", "shared_gallery")
    list_filter = ("available", "brand", "group", "shared_gallery")
    readonly_fields = ("media_preview",)
    fieldsets = (
        (
            "Основное",
            {
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
                    "shared_gallery",
                    "media_preview",
                    "available",
                    "search_tsv",
                ),
            },
        ),
        (
            "SEO",
            {
                "classes": ("tabbed-fieldset",),
                "fields": SEO_FIELD_NAMES,
            },
        ),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("import-xlsx/", self.admin_site.admin_view(self.import_xlsx_view), name="shop_product_import_xlsx"),
            path("export-xlsx/", self.admin_site.admin_view(self.export_xlsx_view), name="shop_product_export_xlsx"),
            path(
                "import-report-xlsx/",
                self.admin_site.admin_view(self.import_report_xlsx_view),
                name="shop_product_import_report_xlsx",
            ),
        ]
        return custom_urls + urls

    def import_xlsx_view(self, request):
        if not self.has_add_permission(request):
            raise PermissionDenied("У вас нет прав на импорт товаров.")

        form = ProductImportForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and form.is_valid():
            try:
                counters, issues = catalog_import_service.import_products_from_workbook(form.cleaned_data["xlsx_file"])
            except ValidationError as exc:
                form.add_error("xlsx_file", exc)
            else:
                request.session["shop_product_import_report"] = {
                    "generated_at": timezone.now().isoformat(),
                    "counters": counters,
                    "issues": issues,
                }
                context = {
                    **self.admin_site.each_context(request),
                    "opts": self.model._meta,
                    "title": "Результат импорта товаров",
                    "subtitle": "Импорт завершён. Ниже показаны итоговые счётчики и замечания по строкам.",
                    "counters": counters,
                    "issues": issues,
                    "report_download_url": reverse("admin:shop_product_import_report_xlsx"),
                    "changelist_url": reverse("admin:shop_product_changelist"),
                    "import_url": reverse("admin:shop_product_import_xlsx"),
                }
                return TemplateResponse(request, "admin/shop/product/import_result.html", context)

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Импорт товаров из XLSX",
            "form": form,
            "subtitle": "Загрузите таблицу с товарами, файлами, SEO-полями и колонками характеристик char_*.",
        }
        return TemplateResponse(request, "admin/shop/product/import_xlsx.html", context)

    def import_report_xlsx_view(self, request):
        report = request.session.get("shop_product_import_report")
        if not report:
            self.message_user(request, "Отчёт по импорту не найден. Сначала выполните импорт.", level=messages.WARNING)
            return HttpResponseRedirect(reverse("admin:shop_product_import_xlsx"))

        payload = catalog_import_service.workbook_bytes_from_import_report(
            report.get("counters") or {},
            report.get("issues") or [],
        )
        response = HttpResponse(
            payload,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="product_import_report.xlsx"'
        return response

    def export_xlsx_view(self, request):
        if not self.has_view_or_change_permission(request):
            raise PermissionDenied("У вас нет прав на экспорт товаров.")

        form = ProductExportForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            mode = form.cleaned_data["mode"]
            selected_group = form.cleaned_data.get("group")
            if mode == ProductExportForm.MODE_SINGLE_GROUP:
                return self._export_single_group_workbook(selected_group)
            if mode == ProductExportForm.MODE_ALL_PRODUCTS:
                return self._export_all_products_workbook()
            return self._export_grouped_zip()

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Экспорт товаров в XLSX",
            "form": form,
            "subtitle": "Можно выгрузить одну категорию, все категории архивом или весь каталог одним Excel-файлом.",
            "submit_label": "Экспортировать",
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
                    catalog_import_service.workbook_bytes_from_headers_and_rows(headers, rows, title="Без категории"),
                )

        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type="application/zip")
        response["Content-Disposition"] = 'attachment; filename="products_by_groups.zip"'
        return response

    def _export_all_products_workbook(self):
        headers, rows = catalog_import_service.build_product_export_rows(Product.objects.order_by("group__name", "name", "id"))
        payload = catalog_import_service.workbook_bytes_from_headers_and_rows(headers, rows, title="Все товары")
        response = HttpResponse(
            payload,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="all_products.xlsx"'
        return response

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        media_assets_service.ensure_single_primary(form.instance)
        media_assets_service.sync_product_media(form.instance)
