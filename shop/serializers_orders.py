from rest_framework import serializers

from shop.models import Inquiry, OrderEmailRecipient, OrderEmailSettings, Product, PublicOrder, PublicOrderItem


class InquiryCreateSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Inquiry
        fields = ["name", "phone", "email", "message"]

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
        fields = ["id", "name", "phone", "email", "message", "created_at"]


class OrderEmailRecipientSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderEmailRecipient
        fields = ["id", "email", "name", "is_active", "created_at", "updated_at"]


class OrderEmailSettingsSerializer(serializers.ModelSerializer):
    is_active = serializers.ReadOnlyField()

    class Meta:
        model = OrderEmailSettings
        fields = [
            "id",
            "title",
            "notification_type",
            "subject",
            "intro_html",
            "body_html",
            "footer_html",
            "is_active",
            "created_at",
            "updated_at",
        ]


class PublicOrderItemCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    qty = serializers.IntegerField(min_value=1)

    def validate_product_id(self, value):
        if not Product.objects.filter(id=value).exists():
            raise serializers.ValidationError("Product does not exist.")
        return value


class PublicOrderCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    address = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    comment = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    items = PublicOrderItemCreateSerializer(many=True)

    class Meta:
        model = PublicOrder
        fields = ["name", "phone", "email", "address", "comment", "items"]

    def validate(self, attrs):
        if not attrs.get("items"):
            raise serializers.ValidationError({"items": "At least one order item is required."})
        return attrs


class PublicOrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source="product.id", read_only=True)
    sku = serializers.CharField(source="product.sku", read_only=True)
    slug = serializers.CharField(source="product.slug", read_only=True)
    name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = PublicOrderItem
        fields = ["id", "product_id", "sku", "slug", "name", "qty"]


class PublicOrderSerializer(serializers.ModelSerializer):
    items = PublicOrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = PublicOrder
        fields = [
            "id",
            "name",
            "phone",
            "email",
            "address",
            "comment",
            "status",
            "total_items",
            "created_at",
            "items",
        ]
