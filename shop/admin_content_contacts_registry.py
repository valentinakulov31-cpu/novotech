from django.contrib import admin
from django.utils.html import escape

from shop.admin_mixins import PublishWorkflowAdminMixin
from shop.admin_support import render_multiline_text
from shop.models import Agent, ContactInfo


@admin.register(ContactInfo)
class ContactInfoAdmin(PublishWorkflowAdminMixin, admin.ModelAdmin):
    singleton_publication = True
    list_display = ("id", "title", "phone", "email", "status", "updated_at", "updated_by", "preview_link")
    list_filter = ("status",)
    search_fields = ("title", "full_name", "address", "schedule", "phone", "email", "yandex_link", "gis_link")
    readonly_fields = ("preview_link", "created_at", "updated_at", "updated_by")
    fields = (
        "title",
        "full_name",
        "address",
        "latitude",
        "longitude",
        "yandex_link",
        "gis_link",
        "schedule",
        "phone",
        "email",
        "status",
        "preview_link",
        "updated_by",
        "created_at",
        "updated_at",
    )

    def render_preview_html(self, obj):
        full_name_block = f"<p><strong>Contact person:</strong> {escape(obj.full_name)}</p>" if obj.full_name else ""
        coordinates_block = (
            f"<p><strong>Coordinates:</strong> {escape(obj.latitude)} / {escape(obj.longitude)}</p>"
            if obj.latitude is not None and obj.longitude is not None
            else ""
        )
        return (
            f"<section><h1>{escape(obj.title)}</h1>"
            f"{full_name_block}"
            f"<p><strong>Address:</strong><br>{render_multiline_text(obj.address)}</p>"
            f"{coordinates_block}"
            f"<p><strong>Yandex:</strong> {escape(obj.yandex_link or '')}</p>"
            f"<p><strong>2GIS:</strong> {escape(obj.gis_link or '')}</p>"
            f"<p><strong>Schedule:</strong><br>{render_multiline_text(obj.schedule)}</p>"
            f"<p><strong>Phone:</strong> {escape(obj.phone)}</p>"
            f"<p><strong>Email:</strong> {escape(obj.email)}</p></section>"
        )


@admin.register(Agent)
class AgentAdmin(PublishWorkflowAdminMixin, admin.ModelAdmin):
    list_display = ("id", "full_name", "position", "email", "phone", "sort_order", "status", "updated_at", "updated_by", "preview_link")
    list_filter = ("status",)
    search_fields = ("full_name", "position", "email", "phone")
    readonly_fields = ("preview_link", "created_at", "updated_at", "updated_by")
    fields = (
        "full_name",
        "position",
        "email",
        "phone",
        "sort_order",
        "status",
        "preview_link",
        "updated_by",
        "created_at",
        "updated_at",
    )

    def render_preview_html(self, obj):
        return (
            f"<section><h1>{escape(obj.full_name)}</h1>"
            f"<p>{escape(obj.position)}</p>"
            f"<p><strong>Phone:</strong> {escape(obj.phone)}</p>"
            f"<p><strong>Email:</strong> {escape(obj.email)}</p></section>"
        )
