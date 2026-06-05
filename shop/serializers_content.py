from django.utils import timezone
from rest_framework import serializers

from shop.models import (
    Agent,
    ContactInfo,
    HtmlContent,
    News,
    NewsAttachment,
    PUBLISH_STATUS_CHOICES,
    PUBLISH_STATUS_DRAFT,
    PUBLISH_STATUS_PUBLISHED,
    Sert,
    Slider,
)


class FileKindFromMimeSerializerMixin:
    def _file_kind_from_mime(self, obj):
        if (obj.mime_type or "").startswith("image/"):
            return "image"
        if (obj.mime_type or "").startswith("video/"):
            return "video"
        return "document"


class NewsCreateSerializer(serializers.Serializer):
    title = serializers.CharField()
    slug = serializers.CharField()
    content = serializers.CharField()
    media = serializers.JSONField(required=False, allow_null=True)
    status = serializers.ChoiceField(choices=[choice[0] for choice in PUBLISH_STATUS_CHOICES], required=False)
    published_at = serializers.DateTimeField(required=False, allow_null=True)
    is_published = serializers.BooleanField(required=False)

    def validate(self, attrs):
        is_published = attrs.pop("is_published", None)
        if "status" not in attrs:
            attrs["status"] = PUBLISH_STATUS_PUBLISHED if is_published else PUBLISH_STATUS_DRAFT
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        payload = validated_data.copy()
        if payload.get("status") == PUBLISH_STATUS_PUBLISHED and not payload.get("published_at"):
            payload["published_at"] = timezone.now()
        if request and request.user.is_authenticated:
            payload["updated_by"] = request.user
        return News.objects.create(**payload)


class NewsAttachmentSerializer(FileKindFromMimeSerializerMixin, serializers.ModelSerializer):
    file_kind = serializers.SerializerMethodField()

    class Meta:
        model = NewsAttachment
        fields = ["id", "news_id", "title", "url", "mime_type", "file_kind", "size_bytes", "sort_order"]

    def get_file_kind(self, obj):
        return self._file_kind_from_mime(obj)


class NewsSerializer(serializers.ModelSerializer):
    attachments = NewsAttachmentSerializer(many=True, read_only=True)
    is_published = serializers.ReadOnlyField()

    class Meta:
        model = News
        fields = ["id", "title", "slug", "content", "media", "published_at", "is_published", "attachments"]


class SertSerializer(FileKindFromMimeSerializerMixin, serializers.ModelSerializer):
    file_kind = serializers.SerializerMethodField()

    class Meta:
        model = Sert
        fields = ["id", "title", "url", "mime_type", "file_kind", "size_bytes", "sort_order"]

    def get_file_kind(self, obj):
        return self._file_kind_from_mime(obj)


class SliderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Slider
        fields = ["id", "image", "title", "text", "slug", "sort_order"]


class HtmlContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = HtmlContent
        fields = ["html_first", "html_second"]


class ContactInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactInfo
        fields = ["title", "full_name", "address", "latitude", "longitude", "yandex_link", "gis_link", "schedule", "phone", "email"]


class AgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = ["id", "full_name", "position", "email", "phone", "sort_order"]
