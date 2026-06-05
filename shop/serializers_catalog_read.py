from rest_framework import serializers

from shop.models import (
    Brand,
    Characteristic,
    City,
    Group,
    Product,
    ProductCertificate,
    ProductCharacteristic,
    ProductGalleryItem,
    ProductMedia,
)
from shop.seo import build_group_seo, build_product_seo
from shop.serializers_catalog_shared import SeoContextSerializerMixin


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["id", "name", "slug", "search_synonyms", "media"]


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ["id", "name", "slug", "name_in_prepositional", "sort_order"]


class GroupSerializer(SeoContextSerializerMixin, serializers.ModelSerializer):
    parent_id = serializers.IntegerField(source="parent.id", allow_null=True, read_only=True)
    seo = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ["id", "parent_id", "name", "slug", "search_synonyms", "description", "media", "seo"]

    def get_seo(self, obj):
        return build_group_seo(obj, city=self._resolved_city())


class ProductMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductMedia
        fields = ["id", "product_id", "url", "mime_type", "media_kind", "size_bytes", "variants", "is_primary", "sort_order", "alt_text"]


class ProductGalleryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductGalleryItem
        fields = ["id", "product_id", "title", "url", "mime_type", "file_kind", "size_bytes", "sort_order"]


class ProductCertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCertificate
        fields = ["id", "product_id", "title", "url", "mime_type", "size_bytes", "sort_order"]


class ProductSerializer(SeoContextSerializerMixin, serializers.ModelSerializer):
    group_id = serializers.IntegerField(source="group.id", allow_null=True, read_only=True)
    brand_id = serializers.IntegerField(source="brand.id", allow_null=True, read_only=True)
    gallery = serializers.SerializerMethodField()
    media_list = serializers.SerializerMethodField()
    certificates_list = serializers.SerializerMethodField()
    seo = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "sku",
            "slug",
            "name",
            "price",
            "currency",
            "description",
            "assortment_html",
            "characteristics_html",
            "group_id",
            "brand_id",
            "media",
            "available",
            "seo",
            "gallery",
            "media_list",
            "certificates_list",
        ]

    def get_media_list(self, obj):
        return ProductMediaSerializer(obj.media_files.all(), many=True).data

    def get_gallery(self, obj):
        return ProductGalleryItemSerializer(obj.gallery_items.all(), many=True).data

    def get_certificates_list(self, obj):
        return ProductCertificateSerializer(obj.certificates.all(), many=True).data

    def get_seo(self, obj):
        return build_product_seo(obj, city=self._resolved_city())


class CharacteristicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Characteristic
        fields = [
            "id",
            "group_id",
            "name",
            "slug",
            "data_type",
            "unit",
            "is_filterable",
            "is_searchable",
        ]


class ProductCharacteristicCreateSerializer(serializers.Serializer):
    attribute_id = serializers.IntegerField()
    value_text = serializers.CharField(required=False, allow_null=True)


class ProductCharacteristicSerializer(serializers.ModelSerializer):
    attribute_id = serializers.IntegerField(source="characteristic.id", read_only=True)
    name = serializers.CharField(source="characteristic.name", read_only=True)
    unit = serializers.CharField(source="characteristic.unit", read_only=True)

    class Meta:
        model = ProductCharacteristic
        fields = ["attribute_id", "name", "unit", "value"]


class CatalogContextSerializer(serializers.Serializer):
    q = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    city_slug = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    group_id = serializers.IntegerField(required=False, allow_null=True)
    group_slug = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    brand_id = serializers.IntegerField(required=False, allow_null=True)
    brand_slug = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class CatalogPriceFilterSerializer(serializers.Serializer):
    min = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    max = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)


class CatalogFiltersSerializer(serializers.Serializer):
    group_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    group_slugs = serializers.ListField(child=serializers.CharField(), required=False)
    brand_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    brand_slugs = serializers.ListField(child=serializers.CharField(), required=False)
    available = serializers.BooleanField(required=False, allow_null=True)
    price = CatalogPriceFilterSerializer(required=False)
    attributes = serializers.JSONField(required=False)


class CatalogQuerySerializer(serializers.Serializer):
    context = CatalogContextSerializer(required=False)
    filters = CatalogFiltersSerializer(required=False)
    page = serializers.IntegerField(required=False, min_value=1)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=100)
    sort = serializers.CharField(required=False)
