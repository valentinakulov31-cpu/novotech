from django.contrib import admin
from django.utils.html import format_html

from shop.admin_forms import (
    NewsAttachmentAdminForm,
    ProductCertificateAdminForm,
    ProductGalleryItemAdminForm,
    ProductMediaAdminForm,
)
from shop.models import NewsAttachment, ProductCertificate, ProductGalleryItem, ProductMedia, PublicOrderItem


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

    @admin.display(description="Preview")
    def preview(self, obj):
        if not obj or not obj.url:
            return "No file"
        return format_html('<a href="{0}" target="_blank">open</a><br><img src="{0}" style="max-height:100px;max-width:140px;" />', obj.url)


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

    @admin.display(description="Certificate")
    def document_link(self, obj):
        if not obj or not obj.url:
            return "No file"
        return format_html('<a href="{0}" target="_blank">{1}</a>', obj.url, obj.title or "open")


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

    @admin.display(description="Gallery file")
    def document_link(self, obj):
        if not obj or not obj.url:
            return "No file"
        return format_html('<a href="{0}" target="_blank">{1}</a>', obj.url, obj.title or "open")


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

    @admin.display(description="Attachment")
    def document_link(self, obj):
        if not obj or not obj.url:
            return "No file"
        return format_html('<a href="{0}" target="_blank">{1}</a>', obj.url, obj.title or "open")


class PublicOrderItemInline(admin.TabularInline):
    model = PublicOrderItem
    extra = 1
    fields = ("product", "qty")
    autocomplete_fields = ("product",)
    can_delete = True
