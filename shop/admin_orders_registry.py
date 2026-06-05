from django.contrib import admin

from shop.admin_forms import OrderEmailSettingsAdminForm
from shop.admin_inlines import PublicOrderItemInline
from shop.admin_mixins import PublishWorkflowAdminMixin
from shop.models import (
    Inquiry,
    OrderEmailRecipient,
    OrderEmailSettings,
    PUBLISH_STATUS_DRAFT,
    PUBLISH_STATUS_PUBLISHED,
    PublicOrder,
    PublicOrderItem,
)
from shop.services.order_email import build_notification_preview_html

@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "phone", "email", "created_at")
    search_fields = ("name", "phone", "email", "message")
    readonly_fields = ("created_at",)
    fields = ("name", "phone", "email", "message", "created_at")


@admin.register(PublicOrder)
class PublicOrderAdmin(admin.ModelAdmin):
    inlines = [PublicOrderItemInline]
    list_display = ("id", "name", "phone", "email", "status", "total_items", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("name", "phone", "email", "address", "comment", "items__product__name", "items__product__sku")
    readonly_fields = ("created_at", "total_items")
    fields = ("name", "phone", "email", "address", "comment", "status", "total_items", "created_at")
    autocomplete_fields = ()

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        order = form.instance
        total_items = sum(order.items.values_list("qty", flat=True))
        if order.total_items != total_items:
            order.total_items = total_items
            order.save(update_fields=["total_items"])


@admin.register(OrderEmailRecipient)
class OrderEmailRecipientAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "name", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("email", "name")
    readonly_fields = ("created_at", "updated_at")
    fields = ("email", "name", "is_active", "created_at", "updated_at")


@admin.register(OrderEmailSettings)
class OrderEmailSettingsAdmin(PublishWorkflowAdminMixin, admin.ModelAdmin):
    form = OrderEmailSettingsAdminForm
    singleton_publication = True
    list_display = ("id", "title", "notification_type", "subject", "status", "updated_at", "updated_by", "preview_link")
    list_filter = ("status",)
    search_fields = ("title", "subject", "notification_type", "intro_html", "footer_html")
    readonly_fields = ("preview_link", "created_at", "updated_at", "updated_by")
    fields = (
        "title",
        "notification_type",
        "subject",
        "intro_html",
        "body_html",
        "footer_html",
        "status",
        "preview_link",
        "updated_by",
        "created_at",
        "updated_at",
    )

    def _unpublish_siblings(self, obj, user):
        siblings = (
            self.model.objects.exclude(pk=obj.pk)
            .filter(status=PUBLISH_STATUS_PUBLISHED, notification_type=obj.notification_type)
        )
        for sibling in siblings:
            sibling.status = PUBLISH_STATUS_DRAFT
            if hasattr(sibling, "updated_by"):
                sibling.updated_by = user
            sibling.save()

    def render_preview_html(self, obj):
        return build_notification_preview_html(obj.notification_type, obj)
