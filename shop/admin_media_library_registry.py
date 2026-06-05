from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse

from shop.admin_support import collect_media_library_assets, delete_media_asset
from shop.models import MediaLibrary


@admin.register(MediaLibrary)
class MediaLibraryAdmin(admin.ModelAdmin):
    change_list_template = "admin/shop/medialibrary/change_list.html"
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "delete-asset/",
                self.admin_site.admin_view(self.delete_asset_view),
                name="shop_medialibrary_delete_asset",
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        if not self.has_view_or_change_permission(request):
            raise PermissionDenied("You do not have permission to view the media library.")
        search_query = request.GET.get("q", "").strip()
        usage_filter = request.GET.get("usage", "").strip()
        usage_options = [
            "Brand image",
            "Group image",
            "Slider image",
            "Product media field",
            "News media field",
            "Product media",
            "Product gallery",
            "Product certificate",
            "News attachment",
            "Sert file",
        ]
        assets = collect_media_library_assets(search_query=search_query, usage_filter=usage_filter)
        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Media library",
            "subtitle": "All uploaded and referenced media in one place.",
            "media_assets": assets,
            "search_query": search_query,
            "usage_filter": usage_filter,
            "usage_options": usage_options,
            "asset_count": len(assets),
            **(extra_context or {}),
        }
        return TemplateResponse(request, self.change_list_template, context)

    def delete_asset_view(self, request):
        if request.method != "POST":
            raise PermissionDenied("POST is required to delete media assets.")
        if not self.has_delete_permission(request):
            raise PermissionDenied("You do not have permission to delete media assets.")

        asset_url = (request.POST.get("asset_url") or "").strip() or None
        asset_storage_path = (request.POST.get("asset_storage_path") or "").strip() or None
        asset_title = (request.POST.get("asset_title") or "").strip() or "media asset"
        search_query = (request.POST.get("q") or "").strip()
        usage_filter = (request.POST.get("usage") or "").strip()
        if not asset_url and not asset_storage_path:
            self.message_user(request, "Media asset identifier is missing.", level=messages.ERROR)
            redirect_url = reverse("admin:shop_medialibrary_changelist")
            query_parts = []
            if search_query:
                query_parts.append(f"q={search_query}")
            if usage_filter:
                query_parts.append(f"usage={usage_filter}")
            if query_parts:
                redirect_url = f"{redirect_url}?{'&'.join(query_parts)}"
            return HttpResponseRedirect(redirect_url)

        with transaction.atomic():
            result = delete_media_asset(asset_url, asset_storage_path)
        deleted_dependency_count = sum(result["deleted_rows"].values())
        cleared_field_count = sum(result["cleared_fields"].values()) + result["updated_products"] + result["updated_news"]
        file_message = " File removed from disk." if result["file_deleted"] else " No local file was removed."
        self.message_user(
            request,
            (
                f"Deleted {asset_title}: dependencies removed {deleted_dependency_count}, "
                f"field references cleared {cleared_field_count}, "
                f"products resynced {result['affected_product_count']}."
                f"{file_message}"
            ),
            level=messages.SUCCESS,
        )
        redirect_url = reverse("admin:shop_medialibrary_changelist")
        query_parts = []
        if search_query:
            query_parts.append(f"q={search_query}")
        if usage_filter:
            query_parts.append(f"usage={usage_filter}")
        if query_parts:
            redirect_url = f"{redirect_url}?{'&'.join(query_parts)}"
        return HttpResponseRedirect(redirect_url)
