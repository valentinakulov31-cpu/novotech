from django import forms
from django.core.exceptions import ValidationError
from tinymce.widgets import TinyMCE

from shop.admin_form_mixins import AdminMediaFormMixin, HtmlTableSanitizerMixin, SeoFieldsAdminFormMixin
from shop.admin_support import SEO_AUTO_HELP_TEXT, SEO_GROUP_PLACEHOLDER_HELP_TEXT
from shop.models import Brand, Characteristic, Group, Product, ProductCharacteristic


class ProductImportForm(forms.Form):
    xlsx_file = forms.FileField(label="XLSX file")

    def clean_xlsx_file(self):
        file = self.cleaned_data["xlsx_file"]
        if not file.name.lower().endswith(".xlsx"):
            raise ValidationError("Upload an .xlsx file.")
        return file


class ProductExportForm(forms.Form):
    group = forms.ModelChoiceField(
        queryset=Group.objects.order_by("name"),
        required=False,
        label="Group",
        help_text="Choose a group to export a single XLSX. Leave empty to download a ZIP with separate files for each group.",
    )


class SynonymListField(forms.JSONField):
    widget = forms.Textarea

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("required", False)
        kwargs.setdefault("help_text", "One synonym per line. The value is stored as a JSON list.")
        super().__init__(*args, **kwargs)

    def prepare_value(self, value):
        if isinstance(value, list):
            return "\n".join(str(item) for item in value if str(item).strip())
        return super().prepare_value(value)

    def to_python(self, value):
        if value in self.empty_values:
            return []
        if isinstance(value, str) and not value.lstrip().startswith("["):
            return [line.strip() for line in value.splitlines() if line.strip()]
        parsed = super().to_python(value)
        if parsed in self.empty_values:
            return []
        if not isinstance(parsed, list):
            raise ValidationError("Enter a list of synonyms.")
        return [str(item).strip() for item in parsed if str(item).strip()]


class BrandAdminForm(AdminMediaFormMixin):
    media_field_name = "media"
    upload_folder_name = "brands"
    search_synonyms = SynonymListField(label="Search synonyms", required=False)

    class Meta:
        model = Brand
        fields = "__all__"


class GroupAdminForm(SeoFieldsAdminFormMixin, AdminMediaFormMixin):
    media_field_name = "media"
    upload_folder_name = "groups"
    search_synonyms = SynonymListField(label="Search synonyms", required=False)
    seo_help_text_by_field = {
        "seo_title": SEO_GROUP_PLACEHOLDER_HELP_TEXT,
        "seo_h1": SEO_GROUP_PLACEHOLDER_HELP_TEXT,
        "seo_description": SEO_GROUP_PLACEHOLDER_HELP_TEXT,
        "seo_keywords": SEO_GROUP_PLACEHOLDER_HELP_TEXT,
        "seo_canonical_url": SEO_GROUP_PLACEHOLDER_HELP_TEXT,
    }

    class Meta:
        model = Group
        fields = "__all__"


class ProductAdminForm(HtmlTableSanitizerMixin, SeoFieldsAdminFormMixin, AdminMediaFormMixin):
    media_field_name = "media"
    upload_folder_name = "products"
    html_field_names = ("assortment_html", "characteristics_html")
    seo_default_help_text = SEO_AUTO_HELP_TEXT

    class Meta:
        model = Product
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["search_tsv"].label = "Search synonyms"
        self.fields["search_tsv"].help_text = (
            "Comma-separated search synonyms and semantic hints. "
            "Example: Р С•Р С–Р Р…Р ВµР В·Р В°РЎвЂ°Р С‘РЎвЂљР В°, Р С•Р С–Р Р…Р ВµР В·Р В°РЎвЂ°Р С‘РЎвЂљР Р…РЎвЂ№Р в„– Р СР В°РЎвЂљР ВµРЎР‚Р С‘Р В°Р В», fireproof, Р С•Р С–Р Р…Р ВµР В·Р В°РЎвЂ°."
        )
        self.fields["assortment_html"].widget = TinyMCE(
            attrs={"cols": 120, "rows": 22},
            mce_attrs={"height": 460},
        )
        self.fields["characteristics_html"].widget = TinyMCE(
            attrs={"cols": 120, "rows": 22},
            mce_attrs={"height": 460},
        )


class ProductCharacteristicAdminForm(forms.ModelForm):
    class Meta:
        model = ProductCharacteristic
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        product = self.initial.get("product") or getattr(self.instance, "product", None)
        product_id = getattr(product, "pk", product)
        if not product_id and self.data:
            product_id = self.data.get("product")
        if product_id:
            selected_product = Product.objects.filter(pk=product_id).first()
            if selected_product and selected_product.group_id:
                self.fields["characteristic"].queryset = Characteristic.objects.filter(group=selected_product.group).order_by("name", "id")
