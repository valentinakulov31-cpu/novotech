from django.contrib import admin
from django.utils.html import escape, format_html

from shop.admin_forms import HtmlContentAdminForm, NewsAdminForm, SliderAdminForm
from shop.admin_inlines import NewsAttachmentInline
from shop.admin_mixins import MediaPreviewAdminMixin, PublishWorkflowAdminMixin
from shop.admin_support import extract_media_url, render_multiline_text
from shop.models import HtmlContent, News, Slider


@admin.register(News)
class NewsAdmin(PublishWorkflowAdminMixin, MediaPreviewAdminMixin, admin.ModelAdmin):
    form = NewsAdminForm
    inlines = [NewsAttachmentInline]
    list_display = ("id", "title", "slug", "status", "published_at", "updated_at", "updated_by", "preview_link")
    search_fields = ("title", "slug")
    list_filter = ("status",)
    readonly_fields = ("media_preview", "created_at", "updated_at", "updated_by", "preview_link")
    fields = (
        "title",
        "slug",
        "content",
        "media",
        "media_upload",
        "media_preview",
        "status",
        "published_at",
        "preview_link",
        "updated_by",
        "created_at",
        "updated_at",
    )

    def render_preview_html(self, obj):
        media_url = extract_media_url(obj.media)
        media_block = ""
        if media_url:
            media_block = f'<p><img src="{escape(media_url)}" style="max-width: 100%; height: auto;" /></p>'
        published_line = f"<p><strong>Published at:</strong> {escape(obj.published_at or 'Not published')}</p>"
        return f"<article>{media_block}<h1>{escape(obj.title)}</h1>{published_line}{obj.content}</article>"


@admin.register(Slider)
class SliderAdmin(PublishWorkflowAdminMixin, admin.ModelAdmin):
    form = SliderAdminForm
    list_display = ("id", "title", "slug", "sort_order", "status", "updated_at", "updated_by", "preview_link")
    list_filter = ("status",)
    search_fields = ("title", "slug", "text")
    readonly_fields = ("image", "image_preview", "preview_link", "created_at", "updated_at", "updated_by")
    fields = (
        "title",
        "slug",
        "text",
        "image_upload",
        "image",
        "image_preview",
        "sort_order",
        "status",
        "preview_link",
        "updated_by",
        "created_at",
        "updated_at",
    )

    @admin.display(description="Preview")
    def image_preview(self, obj):
        if not obj or not obj.image:
            return "No file"
        return format_html('<a href="{0}" target="_blank">open</a><br><img src="{0}" style="max-height:120px;max-width:180px;" />', obj.image)

    def render_preview_html(self, obj):
        image_block = ""
        if obj.image:
            image_block = f'<p><img src="{escape(obj.image)}" style="max-width: 100%; height: auto;" /></p>'
        text_block = f"<div>{render_multiline_text(obj.text)}</div>" if obj.text else ""
        return f"<section>{image_block}<h1>{escape(obj.title)}</h1>{text_block}</section>"


@admin.register(HtmlContent)
class HtmlContentAdmin(PublishWorkflowAdminMixin, admin.ModelAdmin):
    form = HtmlContentAdminForm
    singleton_publication = True
    list_display = ("id", "title", "status", "updated_at", "updated_by", "preview_link")
    list_filter = ("status",)
    search_fields = ("title", "html_first", "html_second")
    readonly_fields = ("preview_link", "created_at", "updated_at", "updated_by")
    fields = (
        "title",
        "html_first",
        "html_second",
        "status",
        "preview_link",
        "updated_by",
        "created_at",
        "updated_at",
    )

    def render_preview_html(self, obj):
        return f"<section>{obj.html_first}<hr>{obj.html_second}</section>"
