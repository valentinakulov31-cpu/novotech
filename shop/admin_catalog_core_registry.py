from django.contrib import admin

from shop.admin_forms import BrandAdminForm, GroupAdminForm, ProductAdminForm, ProductCharacteristicAdminForm
from shop.admin_mixins import MediaPreviewAdminMixin, TabbedFieldsetsAdminMixin
from shop.admin_support import SEO_FIELD_NAMES
from shop.models import Brand, Characteristic, City, Group, Product, ProductCharacteristic
from shop.admin_catalog_import_export import ProductAdminImportExportMixin


@admin.register(Brand)
class BrandAdmin(MediaPreviewAdminMixin, admin.ModelAdmin):
    form = BrandAdminForm
    list_display = ("id", "name", "slug", "media_preview")
    search_fields = ("name", "slug")
    readonly_fields = ("media_preview",)
    fields = ("name", "slug", "search_synonyms", "media", "media_upload", "media_preview")


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "name_in_prepositional", "sort_order", "is_active")
    search_fields = ("name", "slug", "name_in_prepositional")
    list_filter = ("is_active",)
    ordering = ("sort_order", "name", "id")
    fields = ("name", "slug", "name_in_prepositional", "sort_order", "is_active")


@admin.register(Group)
class GroupAdmin(TabbedFieldsetsAdminMixin, MediaPreviewAdminMixin, admin.ModelAdmin):
    form = GroupAdminForm
    list_display = ("id", "name", "slug", "parent", "media_preview")
    search_fields = ("name", "slug", "seo_title", "seo_h1")
    list_filter = ("parent",)
    readonly_fields = ("media_preview",)
    fieldsets = (
        ("РћСЃРЅРѕРІРЅРѕРµ", {
            "classes": ("tabbed-fieldset",),
            "fields": (
                "parent",
                "name",
                "slug",
                "search_synonyms",
                "description",
                "media",
                "media_upload",
                "media_preview",
            ),
        }),
        ("SEO", {
            "classes": ("tabbed-fieldset",),
            "fields": SEO_FIELD_NAMES,
        }),
    )


@admin.register(Product)
class ProductAdmin(ProductAdminImportExportMixin):
    form = ProductAdminForm


@admin.register(Characteristic)
class CharacteristicAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "group", "data_type", "is_filterable", "is_searchable")
    search_fields = ("name", "slug")
    list_filter = ("data_type", "is_filterable", "is_searchable", "group")


@admin.register(ProductCharacteristic)
class ProductCharacteristicAdmin(admin.ModelAdmin):
    form = ProductCharacteristicAdminForm
    list_display = ("id", "product", "characteristic", "value", "created_at")
    search_fields = ("product__name", "characteristic__name", "value")
    list_filter = ("characteristic__group", "characteristic")
    autocomplete_fields = ("product", "characteristic")
