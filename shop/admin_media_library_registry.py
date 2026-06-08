from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.http import urlencode

from shop.admin_media_cleanup_support import delete_unused_media_files
from shop.admin_support import collect_media_library_assets, delete_media_asset
from shop.models import MediaLibrary


USAGE_OPTIONS = [
    "Изображение бренда",
    "Изображение группы",
    "Изображение слайда",
    "Медиа в поле товара",
    "Медиа в поле новости",
    "Основное медиа товара",
    "Галерея товара",
    "Общая галерея товаров",
    "Сертификат товара",
    "Вложение новости",
    "Общий сертификат",
]

MEDIA_LIBRARY_PAGE_SIZE = 100


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
            path("delete-asset/", self.admin_site.admin_view(self.delete_asset_view), name="shop_medialibrary_delete_asset"),
            path("delete-unused/", self.admin_site.admin_view(self.delete_unused_view), name="shop_medialibrary_delete_unused"),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        if not self.has_view_or_change_permission(request):
            raise PermissionDenied("У вас нет прав на просмотр библиотеки медиа.")

        search_query = request.GET.get("q", "").strip()
        usage_filter = request.GET.get("usage", "").strip()
        assets = collect_media_library_assets(search_query=search_query, usage_filter=usage_filter)
        paginator = Paginator(assets, MEDIA_LIBRARY_PAGE_SIZE)
        page_obj = paginator.get_page(request.GET.get("page"))
        pagination_query = urlencode({
            key: value
            for key, value in (
                ("q", search_query),
                ("usage", usage_filter),
            )
            if value
        })
        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Библиотека медиа",
            "subtitle": "Все файлы, найденные в базе и в локальной папке загрузок.",
            "media_assets": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "pagination_query": pagination_query,
            "search_query": search_query,
            "usage_filter": usage_filter,
            "usage_options": USAGE_OPTIONS,
            "asset_count": len(assets),
            "unused_asset_count": sum(1 for asset in assets if asset.get("usage_count", 0) == 0),
            **(extra_context or {}),
        }
        return TemplateResponse(request, self.change_list_template, context)

    def delete_asset_view(self, request):
        if request.method != "POST":
            raise PermissionDenied("Для удаления медиа нужен POST-запрос.")
        if not self.has_delete_permission(request):
            raise PermissionDenied("У вас нет прав на удаление медиа.")

        asset_url = (request.POST.get("asset_url") or "").strip() or None
        asset_storage_path = (request.POST.get("asset_storage_path") or "").strip() or None
        asset_title = (request.POST.get("asset_title") or "").strip() or "файл"
        search_query = (request.POST.get("q") or "").strip()
        usage_filter = (request.POST.get("usage") or "").strip()
        page_number = (request.POST.get("page") or "").strip()

        if not asset_url and not asset_storage_path:
            self.message_user(request, "Не передан идентификатор файла.", level=messages.ERROR)
            return self._redirect_with_filters(search_query, usage_filter, page_number)

        with transaction.atomic():
            result = delete_media_asset(asset_url, asset_storage_path)

        deleted_dependency_count = sum(result["deleted_rows"].values())
        cleared_field_count = sum(result["cleared_fields"].values()) + result["updated_products"] + result["updated_news"]
        file_message = " Файл удалён с диска." if result["file_deleted"] else " Локальный файл не найден или уже был удалён."
        self.message_user(
            request,
            (
                f"Удалён файл «{asset_title}»: удалено зависимостей {deleted_dependency_count}, "
                f"очищено ссылок в полях {cleared_field_count}, "
                f"затронуто товаров {result['affected_product_count']}."
                f"{file_message}"
            ),
            level=messages.SUCCESS,
        )
        return self._redirect_with_filters(search_query, usage_filter, page_number)

    def delete_unused_view(self, request):
        if request.method != "POST":
            raise PermissionDenied("Для удаления неиспользуемых файлов нужен POST-запрос.")
        if not self.has_delete_permission(request):
            raise PermissionDenied("У вас нет прав на удаление файлов.")
        deleted_count = delete_unused_media_files()
        self.message_user(request, f"Удалено неиспользуемых файлов: {deleted_count}.", level=messages.SUCCESS)
        return HttpResponseRedirect(reverse("admin:shop_medialibrary_changelist"))

    def _redirect_with_filters(self, search_query: str, usage_filter: str, page_number: str = ""):
        redirect_url = reverse("admin:shop_medialibrary_changelist")
        query_string = urlencode({
            key: value
            for key, value in (
                ("q", search_query),
                ("usage", usage_filter),
                ("page", page_number),
            )
            if value
        })
        if query_string:
            redirect_url = f"{redirect_url}?{query_string}"
        return HttpResponseRedirect(redirect_url)
