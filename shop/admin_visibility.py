from django.contrib import admin, messages
from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db import transaction

from shop.services.catalog_visibility import set_catalog_visibility


class CatalogVisibilityAdminMixin:
    actions = ("hide_selected", "show_selected")

    @admin.action(description="Скрыть выбранные на сайте", permissions=["change"])
    def hide_selected(self, request, queryset):
        self._set_visibility(request, queryset, hidden=True)

    @admin.action(description="Показать выбранные на сайте", permissions=["change"])
    def show_selected(self, request, queryset):
        self._set_visibility(request, queryset, hidden=False)

    def _set_visibility(self, request, queryset, *, hidden):
        if not self.has_change_permission(request):
            raise PermissionDenied
        message = "Скрыто на сайте" if hidden else "Скрытие на сайте снято"
        with transaction.atomic():
            changed = set_catalog_visibility(queryset, hidden=hidden)
            content_type = ContentType.objects.get_for_model(self.model, for_concrete_model=False)
            LogEntry.objects.bulk_create([
                LogEntry(
                    user_id=request.user.pk, content_type_id=content_type.pk,
                    object_id=str(obj.pk), object_repr=str(obj)[:200],
                    action_flag=CHANGE, change_message=message,
                )
                for obj in changed
            ])
        self.message_user(request, f"{message}. Изменено записей: {len(changed)}.", messages.SUCCESS)
