from django import forms
from tinymce.widgets import TinyMCE

from shop.admin_form_mixins import AdminMediaFormMixin, HtmlTableSanitizerMixin
from shop.admin_support import save_admin_upload
from shop.models import HtmlContent, News, OrderEmailSettings, Slider


class NewsAdminForm(HtmlTableSanitizerMixin, AdminMediaFormMixin):
    media_field_name = "media"
    upload_folder_name = "news"
    html_field_names = ("content",)

    class Meta:
        model = News
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["content"].widget = TinyMCE(
            attrs={"cols": 120, "rows": 24},
            mce_attrs={"height": 520},
        )


class HtmlContentAdminForm(HtmlTableSanitizerMixin, forms.ModelForm):
    html_field_names = ("html_first", "html_second")

    class Meta:
        model = HtmlContent
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["html_first"].widget = TinyMCE(
            attrs={"cols": 120, "rows": 18},
            mce_attrs={"height": 420},
        )
        self.fields["html_second"].widget = TinyMCE(
            attrs={"cols": 120, "rows": 18},
            mce_attrs={"height": 420},
        )


class OrderEmailSettingsAdminForm(HtmlTableSanitizerMixin, forms.ModelForm):
    html_field_names = ("intro_html", "body_html", "footer_html")

    class Meta:
        model = OrderEmailSettings
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["intro_html"].widget = TinyMCE(
            attrs={"cols": 120, "rows": 16},
            mce_attrs={"height": 340},
        )
        self.fields["body_html"].widget = TinyMCE(
            attrs={"cols": 120, "rows": 18},
            mce_attrs={"height": 380},
        )
        self.fields["body_html"].help_text = (
            "For order templates: {{order_id}}, {{name}}, {{phone}}, {{email}}, {{address}}, "
            "{{comment}}, {{total_items}}, {{items_table}}, {{items_text}}. "
            "For inquiry templates: {{inquiry_id}}, {{name}}, {{phone}}, {{email}}, {{message}}, {{created_at}}."
        )
        self.fields["footer_html"].widget = TinyMCE(
            attrs={"cols": 120, "rows": 14},
            mce_attrs={"height": 280},
        )


class SliderAdminForm(forms.ModelForm):
    image_upload = forms.FileField(required=False, label="Upload image")

    class Meta:
        model = Slider
        fields = "__all__"

    def save(self, commit=True):
        instance = super().save(commit=False)
        upload = self.cleaned_data.get("image_upload")
        if upload:
            uploaded = save_admin_upload(upload, "slider")
            instance.image = uploaded["url"]
        if commit:
            instance.save()
            self.save_m2m()
        return instance
