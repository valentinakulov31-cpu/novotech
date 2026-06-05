from rest_framework import serializers

from shop.models import Brand, Group, Product
from shop.serializer_write_helpers import create_model_instance, update_model_instance


class BrandCreateSerializer(serializers.Serializer):
    name = serializers.CharField()
    slug = serializers.CharField()
    search_synonyms = serializers.ListField(child=serializers.CharField(), required=False)
    media = serializers.CharField(required=False, allow_null=True)

    def create(self, validated_data):
        return create_model_instance(Brand, validated_data)

    def update(self, instance, validated_data):
        return update_model_instance(instance, validated_data)


class GroupCreateSerializer(serializers.Serializer):
    parent_id = serializers.IntegerField(required=False, allow_null=True)
    name = serializers.CharField()
    slug = serializers.CharField()
    search_synonyms = serializers.ListField(child=serializers.CharField(), required=False)
    description = serializers.CharField(required=False, allow_null=True)
    media = serializers.CharField(required=False, allow_null=True)
    seo_title = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    seo_h1 = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    seo_description = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    seo_keywords = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    seo_canonical_url = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    seo_robots = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def create(self, validated_data):
        return create_model_instance(Group, validated_data, relation_id_fields=("parent_id",))

    def update(self, instance, validated_data):
        return update_model_instance(instance, validated_data, relation_id_fields=("parent_id",))


class ProductCreateSerializer(serializers.Serializer):
    sku = serializers.CharField()
    slug = serializers.CharField(required=False, allow_blank=True)
    name = serializers.CharField()
    price = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField()
    description = serializers.CharField(required=False, allow_null=True)
    assortment_html = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    characteristics_html = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    group_id = serializers.IntegerField(required=False, allow_null=True)
    brand_id = serializers.IntegerField(required=False, allow_null=True)
    media = serializers.JSONField(required=False, allow_null=True)
    available = serializers.BooleanField(default=True)
    seo_title = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    seo_h1 = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    seo_description = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    seo_keywords = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    seo_canonical_url = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    seo_robots = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def create(self, validated_data):
        return create_model_instance(Product, validated_data, relation_id_fields=("group_id", "brand_id"))

    def update(self, instance, validated_data):
        return update_model_instance(instance, validated_data, relation_id_fields=("group_id", "brand_id"))
