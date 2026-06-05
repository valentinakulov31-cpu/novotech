from django import forms

from shop.admin_support import (
    SEO_FIELD_NAMES,
    mark_generated_file_fields_optional,
    sanitize_catalog_tables,
    save_admin_upload,
    validate_new_file_upload,
)
from shop.file_utils import infer_file_kind


class AdminMediaFormMixin(forms.ModelForm):
    media_upload = forms.FileField(required=False, label="Upload file")
    media_field_name = None
    upload_folder_name = "generic"

    def save(self, commit=True):
        instance = super().save(commit=False)
        upload = self.cleaned_data.get("media_upload")
        if upload:
            uploaded = save_admin_upload(upload, self.upload_folder_name)
            setattr(instance, self.media_field_name, uploaded["url"])
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class HtmlTableSanitizerMixin:
    html_field_names = ()

    def clean(self):
        cleaned_data = super().clean()
        for field_name in self.html_field_names:
            if field_name in cleaned_data:
                cleaned_data[field_name] = sanitize_catalog_tables(cleaned_data.get(field_name))
        return cleaned_data


class SeoFieldsAdminFormMixin:
    seo_optional_fields = SEO_FIELD_NAMES
    seo_help_text_by_field = {}
    seo_default_help_text = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.seo_optional_fields:
            field = self.fields.get(field_name)
            if not field:
                continue
            field.required = False
            help_text = self.seo_help_text_by_field.get(field_name, self.seo_default_help_text)
            if help_text:
                field.help_text = help_text


class UploadedAssetAdminFormMixin(forms.ModelForm):
    upload_field_name = None
    upload_folder_name = "generic"
    generated_optional_fields = ()
    inferred_kind_field_name = None
    title_field_name = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        mark_generated_file_fields_optional(self, extra_fields=list(self.generated_optional_fields))

    def clean(self):
        cleaned_data = super().clean()
        validate_new_file_upload(self, self.upload_field_name)
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        upload = self.cleaned_data.get(self.upload_field_name)
        if upload:
            uploaded = save_admin_upload(upload, self.upload_folder_name)
            instance.storage_path = uploaded["storage_path"]
            instance.url = uploaded["url"]
            instance.mime_type = uploaded["mime_type"]
            instance.size_bytes = uploaded["size_bytes"]
            if self.inferred_kind_field_name:
                setattr(instance, self.inferred_kind_field_name, infer_file_kind(uploaded["mime_type"]))
            if self.title_field_name and not getattr(instance, self.title_field_name):
                setattr(instance, self.title_field_name, upload.name)
        if commit:
            instance.save()
            self.save_m2m()
        return instance
