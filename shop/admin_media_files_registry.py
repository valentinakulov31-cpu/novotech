from django.contrib import admin
from django.utils.html import escape, format_html

from shop.admin_forms import (
    NewsAttachmentAdminForm,
    ProductCertificateAdminForm,
    ProductGalleryItemAdminForm,
    ProductMediaAdminForm,
    SertAdminForm,
)
from shop.admin_inlines import SharedProductGalleryItemInline
from shop.admin_mixins import PublishWorkflowAdminMixin
from shop.models import (
    NewsAttachment,
    ProductCertificate,
    ProductGalleryItem,
    ProductMedia,
    Sert,
    SharedProductGallery,
)
from shop.services import media_assets as media_assets_service


@admin.register(ProductMedia)
class ProductMediaAdmin(admin.ModelAdmin):
    form = ProductMediaAdminForm
    list_display = ("id", "product", "url_preview", "mime_type", "media_kind", "size_bytes", "is_primary", "sort_order")
    list_filter = ("is_primary", "mime_type", "media_kind")
    search_fields = ("product__name", "url", "storage_path")
    readonly_fields = ("url_preview", "storage_path", "url", "mime_type", "media_kind", "size_bytes")
    fields = (
        "product",
        "media_upload",
        "url_preview",
        "storage_path",
        "url",
        "mime_type",
        "media_kind",
        "size_bytes",
        "variants",
        "is_primary",
        "sort_order",
        "alt_text",
    )

    @admin.display(description="Превью")
    def url_preview(self, obj):
        if not obj.url:
            return "Нет файла"
        return format_html('<a href="{0}" target="_blank">открыть</a><br><img src="{0}" style="max-height:120px;max-width:180px;" />', obj.url)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        media_assets_service.ensure_single_primary(obj.product)
        media_assets_service.sync_product_media(obj.product)

    def delete_model(self, request, obj):
        product = obj.product
        super().delete_model(request, obj)
        media_assets_service.ensure_single_primary(product)
        media_assets_service.sync_product_media(product)


@admin.register(ProductGalleryItem)
class ProductGalleryItemAdmin(admin.ModelAdmin):
    form = ProductGalleryItemAdminForm
    list_display = ("id", "product", "title", "file_kind", "mime_type", "size_bytes", "sort_order")
    list_filter = ("file_kind", "mime_type")
    search_fields = ("product__name", "title", "url", "storage_path")
    readonly_fields = ("storage_path", "url", "mime_type", "file_kind", "size_bytes", "document_link")
    fields = (
        "product",
        "gallery_upload",
        "title",
        "document_link",
        "storage_path",
        "url",
        "mime_type",
        "file_kind",
        "size_bytes",
        "sort_order",
    )

    @admin.display(description="Файл галереи")
    def document_link(self, obj):
        if not obj or not obj.url:
            return "Нет файла"
        return format_html('<a href="{0}" target="_blank">{1}</a>', obj.url, obj.title or "открыть")


@admin.register(SharedProductGallery)
class SharedProductGalleryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "linked_products_count")
    search_fields = ("name", "slug", "description")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [SharedProductGalleryItemInline]

    @admin.display(description="Товаров привязано")
    def linked_products_count(self, obj):
        return obj.products.count()


@admin.register(ProductCertificate)
class ProductCertificateAdmin(admin.ModelAdmin):
    form = ProductCertificateAdminForm
    list_display = ("id", "product", "title", "mime_type", "size_bytes", "sort_order")
    search_fields = ("product__name", "title", "url", "storage_path")
    readonly_fields = ("storage_path", "url", "mime_type", "size_bytes", "document_link")
    fields = (
        "product",
        "certificate_upload",
        "title",
        "document_link",
        "storage_path",
        "url",
        "mime_type",
        "size_bytes",
        "sort_order",
    )

    @admin.display(description="Сертификат")
    def document_link(self, obj):
        if not obj or not obj.url:
            return "Нет файла"
        return format_html('<a href="{0}" target="_blank">{1}</a>', obj.url, obj.title or "открыть")


@admin.register(NewsAttachment)
class NewsAttachmentAdmin(admin.ModelAdmin):
    form = NewsAttachmentAdminForm
    list_display = ("id", "news", "title", "mime_type", "size_bytes", "sort_order")
    search_fields = ("news__title", "title", "url", "storage_path")
    readonly_fields = ("storage_path", "url", "mime_type", "size_bytes", "document_link")
    fields = (
        "news",
        "attachment_upload",
        "title",
        "document_link",
        "storage_path",
        "url",
        "mime_type",
        "size_bytes",
        "sort_order",
    )

    @admin.display(description="Вложение")
    def document_link(self, obj):
        if not obj or not obj.url:
            return "Нет файла"
        return format_html('<a href="{0}" target="_blank">{1}</a>', obj.url, obj.title or "открыть")


@admin.register(Sert)
class SertAdmin(PublishWorkflowAdminMixin, admin.ModelAdmin):
    form = SertAdminForm
    list_display = ("id", "title", "mime_type", "size_bytes", "sort_order", "status", "updated_at", "updated_by", "preview_link")
    list_filter = ("status", "mime_type")
    search_fields = ("title", "url", "storage_path")
    readonly_fields = ("storage_path", "url", "mime_type", "size_bytes", "document_link", "preview_link", "created_at", "updated_at", "updated_by")
    fields = (
        "title",
        "file_upload",
        "document_link",
        "storage_path",
        "url",
        "mime_type",
        "size_bytes",
        "sort_order",
        "status",
        "preview_link",
        "updated_by",
        "created_at",
        "updated_at",
    )

    @admin.display(description="Файл")
    def document_link(self, obj):
        if not obj or not obj.url:
            return "Нет файла"
        return format_html('<a href="{0}" target="_blank">{1}</a>', obj.url, obj.title or "открыть")

    def render_preview_html(self, obj):
        if (obj.mime_type or "").startswith("image/"):
            return f'<section><h1>{escape(obj.title)}</h1><p><img src="{escape(obj.url)}" style="max-width: 100%; height: auto;" /></p></section>'
        if (obj.mime_type or "").startswith("video/"):
            return (
                f'<section><h1>{escape(obj.title)}</h1>'
                f'<video src="{escape(obj.url)}" controls style="max-width: 100%;"></video></section>'
            )
        return (
            f'<section><h1>{escape(obj.title)}</h1>'
            f'<p><a href="{escape(obj.url)}" target="_blank">Открыть файл</a></p></section>'
        )
