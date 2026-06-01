"""
Serializers for shop API
"""
from rest_framework import serializers
from shop.seo import build_group_seo, build_product_seo, resolve_city
from shop.models import (
    Brand, City, Group, Product, ProductMedia,
    ProductGalleryItem, ProductCertificate, Characteristic, ProductCharacteristic,
    News, NewsAttachment, Sert, Slider, Inquiry, HtmlContent, ContactInfo, Agent, PublicOrder,
    PublicOrderItem, OrderEmailRecipient, OrderEmailSettings, PUBLISH_STATUS_CHOICES,
    PUBLISH_STATUS_DRAFT, PUBLISH_STATUS_PUBLISHED,
)


# Brands

class BrandCreateSerializer(serializers.Serializer):
    name = serializers.CharField()
    slug = serializers.CharField()
    search_synonyms = serializers.ListField(child=serializers.CharField(), required=False)
    media = serializers.CharField(required=False, allow_null=True)


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['id', 'name', 'slug', 'search_synonyms', 'media']


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ['id', 'name', 'slug', 'name_in_prepositional', 'sort_order']


# Groups

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


class GroupSerializer(serializers.ModelSerializer):
    parent_id = serializers.IntegerField(source='parent.id', allow_null=True, read_only=True)
    seo = serializers.SerializerMethodField()
    
    class Meta:
        model = Group
        fields = ['id', 'parent_id', 'name', 'slug', 'search_synonyms', 'description', 'media', 'seo']

    def _resolved_city(self):
        if hasattr(self, "_cached_city"):
            return self._cached_city
        request = self.context.get('request') if hasattr(self, 'context') else None
        city_slug = request.query_params.get('city_slug') if request else None
        self._cached_city = resolve_city(city_slug=city_slug)
        return self._cached_city

    def get_seo(self, obj):
        return build_group_seo(obj, city=self._resolved_city())


# Products

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


class ProductSerializer(serializers.ModelSerializer):
    group_id = serializers.IntegerField(source='group.id', allow_null=True, read_only=True)
    brand_id = serializers.IntegerField(source='brand.id', allow_null=True, read_only=True)
    gallery = serializers.SerializerMethodField()
    media_list = serializers.SerializerMethodField()
    certificates_list = serializers.SerializerMethodField()
    seo = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = ['id', 'sku', 'slug', 'name', 'price', 'currency', 'description', 'assortment_html', 'characteristics_html',
                  'group_id', 'brand_id', 'media', 'available', 'seo', 'gallery',
                  'media_list', 'certificates_list']

    def _serialize_media(self, obj):
        items = obj.media_files.all()
        return ProductMediaSerializer(items, many=True).data

    def get_media_list(self, obj):
        return self._serialize_media(obj)

    def get_gallery(self, obj):
        items = obj.gallery_items.all()
        return ProductGalleryItemSerializer(items, many=True).data

    def get_certificates_list(self, obj):
        items = obj.certificates.all()
        return ProductCertificateSerializer(items, many=True).data

    def _resolved_city(self):
        if hasattr(self, "_cached_city"):
            return self._cached_city
        request = self.context.get('request') if hasattr(self, 'context') else None
        city_slug = request.query_params.get('city_slug') if request else None
        self._cached_city = resolve_city(city_slug=city_slug)
        return self._cached_city

    def get_seo(self, obj):
        return build_product_seo(obj, city=self._resolved_city())


# Media

class ProductMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductMedia
        fields = ['id', 'product_id', 'url', 'mime_type', 
                  'media_kind', 'size_bytes', 'variants', 'is_primary', 'sort_order', 'alt_text']


class ProductGalleryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductGalleryItem
        fields = ['id', 'product_id', 'title', 'url', 'mime_type', 'file_kind', 'size_bytes', 'sort_order']


class ProductCertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCertificate
        fields = ['id', 'product_id', 'title', 'url', 'mime_type', 'size_bytes', 'sort_order']


# Characteristics

class CharacteristicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Characteristic
        fields = [
            'id',
            'group_id',
            'name',
            'slug',
            'data_type',
            'unit',
            'is_filterable',
            'is_searchable',
        ]


class ProductCharacteristicCreateSerializer(serializers.Serializer):
    attribute_id = serializers.IntegerField()
    value_text = serializers.CharField(required=False, allow_null=True)


class ProductCharacteristicSerializer(serializers.ModelSerializer):
    attribute_id = serializers.IntegerField(source='characteristic.id', read_only=True)
    name = serializers.CharField(source='characteristic.name', read_only=True)
    unit = serializers.CharField(source='characteristic.unit', read_only=True)
    
    class Meta:
        model = ProductCharacteristic
        fields = ['attribute_id', 'name', 'unit', 'value']


# News

class NewsCreateSerializer(serializers.Serializer):
    title = serializers.CharField()
    slug = serializers.CharField()
    content = serializers.CharField()
    media = serializers.JSONField(required=False, allow_null=True)
    status = serializers.ChoiceField(choices=[choice[0] for choice in PUBLISH_STATUS_CHOICES], required=False)
    published_at = serializers.DateTimeField(required=False, allow_null=True)
    is_published = serializers.BooleanField(required=False)

    def validate(self, attrs):
        is_published = attrs.pop('is_published', None)
        if 'status' not in attrs:
            attrs['status'] = PUBLISH_STATUS_PUBLISHED if is_published else PUBLISH_STATUS_DRAFT
        return attrs


class NewsAttachmentSerializer(serializers.ModelSerializer):
    file_kind = serializers.SerializerMethodField()

    class Meta:
        model = NewsAttachment
        fields = ['id', 'news_id', 'title', 'url', 'mime_type', 'file_kind', 'size_bytes', 'sort_order']

    def get_file_kind(self, obj):
        if (obj.mime_type or '').startswith('image/'):
            return 'image'
        if (obj.mime_type or '').startswith('video/'):
            return 'video'
        return 'document'


class NewsSerializer(serializers.ModelSerializer):
    attachments = NewsAttachmentSerializer(many=True, read_only=True)
    is_published = serializers.ReadOnlyField()

    class Meta:
        model = News
        fields = ['id', 'title', 'slug', 'content', 'media', 'published_at', 'is_published', 'attachments']


class SertSerializer(serializers.ModelSerializer):
    file_kind = serializers.SerializerMethodField()

    class Meta:
        model = Sert
        fields = ['id', 'title', 'url', 'mime_type', 'file_kind', 'size_bytes', 'sort_order']

    def get_file_kind(self, obj):
        if (obj.mime_type or '').startswith('image/'):
            return 'image'
        if (obj.mime_type or '').startswith('video/'):
            return 'video'
        return 'document'


class SliderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Slider
        fields = ['id', 'image', 'title', 'text', 'slug', 'sort_order']


class InquiryCreateSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Inquiry
        fields = ['name', 'phone', 'email', 'message']

    def validate(self, attrs):
        phone = str(attrs.get("phone") or "").strip()
        email = str(attrs.get("email") or "").strip()
        if not phone and not email:
            raise serializers.ValidationError(
                {"non_field_errors": ["At least one contact is required: phone or email."]}
            )
        return attrs


class InquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inquiry
        fields = ['id', 'name', 'phone', 'email', 'message', 'created_at']


class HtmlContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = HtmlContent
        fields = ['html_first', 'html_second']


class ContactInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactInfo
        fields = ['title', 'full_name', 'address', 'latitude', 'longitude', 'yandex_link', 'gis_link', 'schedule', 'phone', 'email']


class AgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = ['id', 'full_name', 'position', 'email', 'phone', 'sort_order']


class OrderEmailRecipientSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderEmailRecipient
        fields = ['id', 'email', 'name', 'is_active', 'created_at', 'updated_at']


class OrderEmailSettingsSerializer(serializers.ModelSerializer):
    is_active = serializers.ReadOnlyField()

    class Meta:
        model = OrderEmailSettings
        fields = [
            'id',
            'title',
            'notification_type',
            'subject',
            'intro_html',
            'body_html',
            'footer_html',
            'is_active',
            'created_at',
            'updated_at',
        ]


class PublicOrderItemCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    qty = serializers.IntegerField(min_value=1)

    def validate_product_id(self, value):
        if not Product.objects.filter(id=value).exists():
            raise serializers.ValidationError('Product does not exist.')
        return value


class PublicOrderCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    address = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    comment = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    items = PublicOrderItemCreateSerializer(many=True)

    class Meta:
        model = PublicOrder
        fields = ['name', 'phone', 'email', 'address', 'comment', 'items']

    def validate(self, attrs):
        if not attrs.get('items'):
            raise serializers.ValidationError({'items': 'At least one order item is required.'})
        return attrs


class PublicOrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source='product.id', read_only=True)
    sku = serializers.CharField(source='product.sku', read_only=True)
    slug = serializers.CharField(source='product.slug', read_only=True)
    name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = PublicOrderItem
        fields = ['id', 'product_id', 'sku', 'slug', 'name', 'qty']


class PublicOrderSerializer(serializers.ModelSerializer):
    items = PublicOrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = PublicOrder
        fields = [
            'id',
            'name',
            'phone',
            'email',
            'address',
            'comment',
            'status',
            'total_items',
            'created_at',
            'items',
        ]


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
