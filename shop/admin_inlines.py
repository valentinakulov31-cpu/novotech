from django.contrib import admin
from django.utils.html import format_html

from shop.admin_forms import (
    NewsAttachmentAdminForm,
    ProductCertificateAdminForm,
    ProductGalleryItemAdminForm,
    ProductMediaAdminForm,
    SharedProductGalleryItemAdminForm,
)
from shop.models import NewsAttachment, ProductCertificate, ProductGalleryItem, ProductMedia, PublicOrderItem, SharedProductGalleryItem


class ProductMediaInlineForm(ProductMediaAdminForm):
    class Meta(ProductMediaAdminForm.Meta):
        model = ProductMedia
        fields = "__all__"


class ProductMediaInline(admin.TabularInline):
    model = ProductMedia
    form = ProductMediaInlineForm
    extra = 1
    fields = (
        "media_upload",
        "preview",
        "media_kind",
        "mime_type",
        "size_bytes",
        "is_primary",
        "sort_order",
        "alt_text",
    )
    readonly_fields = ("preview", "media_kind", "mime_type", "size_bytes")
    ordering = ("-is_primary", "sort_order", "id")

    @admin.display(description="Превью")
    def preview(self, obj):
        if not obj or not obj.url:
            return "Нет файла"
        return format_html('<a href="{0}" target="_blank">открыть</a><br><img src="{0}" style="max-height:100px;max-width:140px;" />', obj.url)


class ProductCertificateInline(admin.TabularInline):
    model = ProductCertificate
    form = ProductCertificateAdminForm
    extra = 1
    fields = (
        "certificate_upload",
        "title",
        "document_link",
        "mime_type",
        "size_bytes",
        "sort_order",
    )
    readonly_fields = ("document_link", "mime_type", "size_bytes")
    ordering = ("sort_order", "id")

    @admin.display(description="Сертификат")
    def document_link(self, obj):
        if not obj or not obj.url:
            return "Нет файла"
        return format_html('<a href="{0}" target="_blank">{1}</a>', obj.url, obj.title or "открыть")


class ProductGalleryItemInline(admin.TabularInline):
    model = ProductGalleryItem
    form = ProductGalleryItemAdminForm
    extra = 1
    fields = (
        "gallery_upload",
        "title",
        "file_kind",
        "document_link",
        "mime_type",
        "size_bytes",
        "sort_order",
    )
    readonly_fields = ("file_kind", "document_link", "mime_type", "size_bytes")
    ordering = ("sort_order", "id")

    @admin.display(description="Файл галереи")
    def document_link(self, obj):
        if not obj or not obj.url:
            return "Нет файла"
        return format_html('<a href="{0}" target="_blank">{1}</a>', obj.url, obj.title or "открыть")


class SharedProductGalleryItemInline(admin.TabularInline):
    model = SharedProductGalleryItem
    form = SharedProductGalleryItemAdminForm
    extra = 1
    fields = (
        "gallery_upload",
        "title",
        "file_kind",
        "document_link",
        "mime_type",
        "size_bytes",
        "sort_order",
    )
    readonly_fields = ("file_kind", "document_link", "mime_type", "size_bytes")
    ordering = ("sort_order", "id")

    @admin.display(description="Файл общей галереи")
    def document_link(self, obj):
        if not obj or not obj.url:
            return "Нет файла"
        return format_html('<a href="{0}" target="_blank">{1}</a>', obj.url, obj.title or "открыть")


class NewsAttachmentInline(admin.TabularInline):
    model = NewsAttachment
    form = NewsAttachmentAdminForm
    extra = 1
    fields = (
        "attachment_upload",
        "title",
        "document_link",
        "mime_type",
        "size_bytes",
        "sort_order",
    )
    readonly_fields = ("document_link", "mime_type", "size_bytes")
    ordering = ("sort_order", "id")

    @admin.display(description="Вложение")
    def document_link(self, obj):
        if not obj or not obj.url:
            return "Нет файла"
        return format_html('<a href="{0}" target="_blank">{1}</a>', obj.url, obj.title or "открыть")


class PublicOrderItemInline(admin.TabularInline):
    model = PublicOrderItem
    extra = 1
    fields = ("product", "qty")
    autocomplete_fields = ("product",)
    can_delete = True
