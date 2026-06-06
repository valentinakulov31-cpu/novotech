from django import forms

from shop.admin_form_mixins import UploadedAssetAdminFormMixin
from shop.models import NewsAttachment, ProductCertificate, ProductGalleryItem, ProductMedia, Sert, SharedProductGalleryItem


class ProductMediaAdminForm(UploadedAssetAdminFormMixin):
    media_upload = forms.FileField(required=False, label="Upload file")
    upload_field_name = "media_upload"
    upload_folder_name = "product_media"
    generated_optional_fields = ("media_kind",)
    inferred_kind_field_name = "media_kind"

    class Meta:
        model = ProductMedia
        fields = "__all__"


class ProductCertificateAdminForm(UploadedAssetAdminFormMixin):
    certificate_upload = forms.FileField(required=False, label="Upload certificate")
    upload_field_name = "certificate_upload"
    upload_folder_name = "product_certificates"
    title_field_name = "title"

    class Meta:
        model = ProductCertificate
        fields = "__all__"


class ProductGalleryItemAdminForm(UploadedAssetAdminFormMixin):
    gallery_upload = forms.FileField(required=False, label="Upload gallery file")
    upload_field_name = "gallery_upload"
    upload_folder_name = "product_gallery"
    generated_optional_fields = ("file_kind",)
    inferred_kind_field_name = "file_kind"
    title_field_name = "title"

    class Meta:
        model = ProductGalleryItem
        fields = "__all__"


class SharedProductGalleryItemAdminForm(UploadedAssetAdminFormMixin):
    gallery_upload = forms.FileField(required=False, label="Загрузить файл галереи")
    upload_field_name = "gallery_upload"
    upload_folder_name = "shared_product_gallery"
    generated_optional_fields = ("file_kind",)
    inferred_kind_field_name = "file_kind"
    title_field_name = "title"

    class Meta:
        model = SharedProductGalleryItem
        fields = "__all__"


class NewsAttachmentAdminForm(UploadedAssetAdminFormMixin):
    attachment_upload = forms.FileField(required=False, label="Upload attachment")
    upload_field_name = "attachment_upload"
    upload_folder_name = "news_attachments"
    title_field_name = "title"

    class Meta:
        model = NewsAttachment
        fields = "__all__"


class SertAdminForm(UploadedAssetAdminFormMixin):
    file_upload = forms.FileField(required=False, label="Upload file")
    upload_field_name = "file_upload"
    upload_folder_name = "serts"
    title_field_name = "title"

    class Meta:
        model = Sert
        fields = "__all__"
