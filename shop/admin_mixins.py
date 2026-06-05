from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe

from shop.admin_support import extract_media_url
from shop.models import PUBLISH_STATUS_DRAFT, PUBLISH_STATUS_PUBLISHED


class TabbedFieldsetsAdminMixin:
    class Media:
        css = {"all": ("shop/css/admin_tabbed_fieldsets.css",)}
        js = ("shop/js/admin_tabbed_fieldsets.js",)


class PublishWorkflowAdminMixin:
    preview_template_name = "admin/shop/content_preview.html"
    singleton_publication = False
    actions = ("publish_selected", "move_to_draft")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/preview/",
                self.admin_site.admin_view(self.preview_view),
                name=f"{self.model._meta.app_label}_{self.model._meta.model_name}_preview",
            ),
        ]
        return custom_urls + urls

    def save_model(self, request, obj, form, change):
        previous_status = None
        if change:
            previous = self.model.objects.filter(pk=obj.pk).only("status").first()
            previous_status = previous.status if previous else None

        if hasattr(obj, "updated_by") and request.user.is_authenticated:
            obj.updated_by = request.user

        if hasattr(obj, "published_at") and obj.status == PUBLISH_STATUS_PUBLISHED:
            if previous_status != PUBLISH_STATUS_PUBLISHED or not obj.published_at:
                obj.published_at = timezone.now()

        super().save_model(request, obj, form, change)
        if obj.status == PUBLISH_STATUS_PUBLISHED:
            self._unpublish_siblings(obj, request.user if request.user.is_authenticated else None)

    def _unpublish_siblings(self, obj, user):
        if not self.singleton_publication:
            return
        siblings = self.model.objects.exclude(pk=obj.pk).filter(status=PUBLISH_STATUS_PUBLISHED)
        for sibling in siblings:
            sibling.status = PUBLISH_STATUS_DRAFT
            if hasattr(sibling, "updated_by"):
                sibling.updated_by = user
            sibling.save()

    @admin.action(description="Publish selected items")
    def publish_selected(self, request, queryset):
        if self.singleton_publication and queryset.count() > 1:
            self.message_user(request, "Select only one record to publish for this section.", level=messages.ERROR)
            return

        published_count = 0
        for obj in queryset:
            obj.status = PUBLISH_STATUS_PUBLISHED
            if hasattr(obj, "updated_by") and request.user.is_authenticated:
                obj.updated_by = request.user
            if hasattr(obj, "published_at"):
                obj.published_at = timezone.now()
            obj.save()
            self._unpublish_siblings(obj, request.user if request.user.is_authenticated else None)
            published_count += 1

        self.message_user(request, f"Published items: {published_count}.", level=messages.SUCCESS)

    @admin.action(description="Move selected items to draft")
    def move_to_draft(self, request, queryset):
        updated_count = 0
        for obj in queryset:
            obj.status = PUBLISH_STATUS_DRAFT
            if hasattr(obj, "updated_by") and request.user.is_authenticated:
                obj.updated_by = request.user
            obj.save()
            updated_count += 1

        self.message_user(request, f"Draft items: {updated_count}.", level=messages.SUCCESS)

    @admin.display(description="Preview")
    def preview_link(self, obj):
        if not obj or not obj.pk:
            return "Save to preview"
        url = reverse(f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_preview", args=[obj.pk])
        return format_html('<a href="{}" target="_blank">open preview</a>', url)

    def preview_view(self, request, object_id):
        obj = self.get_object(request, object_id)
        if obj is None:
            raise PermissionDenied("Object not found.")
        if not self.has_view_or_change_permission(request, obj):
            raise PermissionDenied("You do not have permission to preview this object.")

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "object": obj,
            "title": f"Preview: {obj}",
            "preview_html": mark_safe(self.render_preview_html(obj)),
            "back_url": reverse(f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_change", args=[obj.pk]),
            "history_url": reverse(f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_history", args=[obj.pk]),
        }
        return TemplateResponse(request, self.preview_template_name, context)

    def render_preview_html(self, obj):
        return f"<pre>{escape(str(obj))}</pre>"


class MediaPreviewAdminMixin:
    @admin.display(description="Preview")
    def media_preview(self, obj):
        url = extract_media_url(getattr(obj, "media", None))
        if not url:
            return "No file"
        return format_html('<a href="{0}" target="_blank">open</a><br><img src="{0}" style="max-height:120px;max-width:180px;" />', url)
