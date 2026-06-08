from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.urls import path, reverse
from django.utils.html import format_html

from shop.admin_catalog_import_export import ProductAdminImportExportMixin
from shop.admin_forms import BrandAdminForm, GroupAdminForm, ProductAdminForm, ProductCharacteristicAdminForm
from shop.admin_inlines import CharacteristicInline
from shop.admin_mixins import MediaPreviewAdminMixin, TabbedFieldsetsAdminMixin
from shop.admin_support import SEO_FIELD_NAMES
from shop.models import Brand, CatalogImportJob, Characteristic, City, Group, Product, ProductCharacteristic
from shop.services import catalog_import_jobs as catalog_import_jobs_service


@admin.register(Brand)
class BrandAdmin(MediaPreviewAdminMixin, admin.ModelAdmin):
    form = BrandAdminForm
    list_display = ("id", "name", "slug", "media_preview")
    search_fields = ("name", "slug")
    readonly_fields = ("media_preview",)
    fields = ("name", "slug", "search_synonyms", "media", "media_upload", "media_preview")


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "name_in_prepositional", "sort_order", "is_active")
    search_fields = ("name", "slug", "name_in_prepositional")
    list_filter = ("is_active",)
    ordering = ("sort_order", "name", "id")
    fields = ("name", "slug", "name_in_prepositional", "sort_order", "is_active")


@admin.register(Group)
class GroupAdmin(TabbedFieldsetsAdminMixin, MediaPreviewAdminMixin, admin.ModelAdmin):
    form = GroupAdminForm
    inlines = (CharacteristicInline,)
    list_display = ("id", "name", "slug", "parent", "media_preview")
    search_fields = ("name", "slug", "seo_title", "seo_h1")
    list_filter = ("parent",)
    readonly_fields = ("media_preview",)
    fieldsets = (
        (
            "Основное",
            {
                "classes": ("tabbed-fieldset",),
                "fields": (
                    "parent",
                    "name",
                    "slug",
                    "search_synonyms",
                    "description",
                    "media",
                    "media_upload",
                    "media_preview",
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


@admin.register(Product)
class ProductAdmin(ProductAdminImportExportMixin):
    form = ProductAdminForm


@admin.register(CatalogImportJob)
class CatalogImportJobAdmin(admin.ModelAdmin):
    change_form_template = "admin/shop/catalogimportjob/change_form.html"
    list_display = ("id", "original_filename", "status_badge", "created_by", "created_at", "started_at", "finished_at")
    list_filter = ("status", "created_at", "started_at", "finished_at")
    search_fields = ("id", "original_filename", "fatal_error", "created_by__username")
    readonly_fields = (
        "status_badge",
        "queue_name",
        "original_filename",
        "created_by",
        "created_at",
        "started_at",
        "finished_at",
        "source_file_link",
        "report_download_link",
        "fatal_error_block",
        "counters_block",
        "issues_block",
    )
    fields = (
        "status_badge",
        "queue_name",
        "original_filename",
        "created_by",
        "created_at",
        "started_at",
        "finished_at",
        "source_file_link",
        "report_download_link",
        "fatal_error_block",
        "counters_block",
        "issues_block",
    )

    def has_add_permission(self, request):
        return False

    @admin.display(description="Статус")
    def status_badge(self, obj):
        palette = {
            CatalogImportJob.STATUS_QUEUED: ("#2563eb", "В очереди"),
            CatalogImportJob.STATUS_PROCESSING: ("#d97706", "Обрабатывается"),
            CatalogImportJob.STATUS_SUCCEEDED: ("#059669", "Завершён"),
            CatalogImportJob.STATUS_FAILED: ("#dc2626", "Ошибка"),
        }
        color, label = palette.get(obj.status, ("#475569", obj.get_status_display()))
        return format_html(
            '<span style="display:inline-block;padding:4px 10px;border-radius:999px;background:{};color:#fff;font-weight:600;">{}</span>',
            color,
            label,
        )

    @admin.display(description="Загруженный файл")
    def source_file_link(self, obj):
        if not obj.source_file:
            return "Нет файла"
        return format_html('<a href="{}" target="_blank">{}</a>', obj.source_file.url, obj.original_filename)

    @admin.display(description="Отчёт XLSX")
    def report_download_link(self, obj):
        if not obj.is_finished:
            return "Отчёт станет доступен после завершения."
        if obj.status != CatalogImportJob.STATUS_SUCCEEDED and not obj.issues:
            return "Нет отчёта"
        url = reverse("admin:shop_catalogimportjob_report_xlsx", args=[obj.pk])
        return format_html('<a class="button" href="{}">Скачать отчёт XLSX</a>', url)

    @admin.display(description="Фатальная ошибка")
    def fatal_error_block(self, obj):
        if not obj.fatal_error:
            return "Нет"
        return format_html("<pre style='white-space:pre-wrap;margin:0;'>{}</pre>", obj.fatal_error)

    @admin.display(description="Счётчики")
    def counters_block(self, obj):
        if not obj.counters:
            return "Пока нет данных"
        rows = "".join(
            f"<tr><th style='text-align:left;padding:6px 10px;'>{key}</th><td style='padding:6px 10px;'>{value}</td></tr>"
            for key, value in obj.counters.items()
        )
        return format_html(
            "<table style='border-collapse:collapse;min-width:360px;'><tbody>{}</tbody></table>",
            format_html(rows),
        )

    @admin.display(description="Ошибки и предупреждения")
    def issues_block(self, obj):
        if not obj.issues:
            return "Нет замечаний"
        header = (
            "<tr>"
            "<th style='padding:6px 10px;'>Уровень</th>"
            "<th style='padding:6px 10px;'>Строка</th>"
            "<th style='padding:6px 10px;'>SKU</th>"
            "<th style='padding:6px 10px;'>Колонка</th>"
            "<th style='padding:6px 10px;'>Код</th>"
            "<th style='padding:6px 10px;'>Сообщение</th>"
            "</tr>"
        )
        rows = "".join(
            (
                "<tr>"
                f"<td style='padding:6px 10px;'>{issue.get('level', '')}</td>"
                f"<td style='padding:6px 10px;'>{issue.get('row_number', '')}</td>"
                f"<td style='padding:6px 10px;'>{issue.get('sku', '')}</td>"
                f"<td style='padding:6px 10px;'>{issue.get('column', '')}</td>"
                f"<td style='padding:6px 10px;'><code>{issue.get('code', '')}</code></td>"
                f"<td style='padding:6px 10px;'>{issue.get('message', '')}</td>"
                "</tr>"
            )
            for issue in obj.issues
        )
        return format_html(
            "<table style='border-collapse:collapse;width:100%;'><thead>{}</thead><tbody>{}</tbody></table>",
            format_html(header),
            format_html(rows),
        )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/report-xlsx/",
                self.admin_site.admin_view(self.report_xlsx_view),
                name="shop_catalogimportjob_report_xlsx",
            ),
        ]
        return custom_urls + urls

    def render_change_form(self, request, context, *args, **kwargs):
        obj = context.get("original")
        context["refresh_seconds"] = catalog_import_jobs_service.get_catalog_import_refresh_seconds(obj) if obj else 0
        return super().render_change_form(request, context, *args, **kwargs)

    def report_xlsx_view(self, request, object_id):
        job = self.get_object(request, object_id)
        if job is None:
            raise PermissionDenied
        payload = catalog_import_jobs_service.build_catalog_import_report(job)
        response = HttpResponse(
            payload,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="catalog_import_job_{job.pk}.xlsx"'
        return response


@admin.register(Characteristic)
class CharacteristicAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "group", "data_type", "is_filterable", "is_searchable")
    search_fields = ("name", "slug")
    list_filter = ("data_type", "is_filterable", "is_searchable", "group")


@admin.register(ProductCharacteristic)
class ProductCharacteristicAdmin(admin.ModelAdmin):
    form = ProductCharacteristicAdminForm
    list_display = ("id", "product", "characteristic", "value", "created_at")
    search_fields = ("product__name", "characteristic__name", "value")
    list_filter = ("characteristic__group", "characteristic")
    autocomplete_fields = ("product", "characteristic")
