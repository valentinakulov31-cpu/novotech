from django import forms
from django.core.exceptions import ValidationError
from tinymce.widgets import TinyMCE

from shop.admin_form_mixins import AdminMediaFormMixin, HtmlTableSanitizerMixin, SeoFieldsAdminFormMixin
from shop.admin_support import SEO_AUTO_HELP_TEXT, SEO_GROUP_PLACEHOLDER_HELP_TEXT
from shop.model_utils import transliterate_slug
from shop.models import Brand, Characteristic, Group, Product, ProductCharacteristic


class ProductImportForm(forms.Form):
    xlsx_file = forms.FileField(label="Файл XLSX")

    def clean_xlsx_file(self):
        file = self.cleaned_data["xlsx_file"]
        if not file.name.lower().endswith(".xlsx"):
            raise ValidationError("Загрузите файл в формате .xlsx.")
        return file


class ProductExportForm(forms.Form):
    MODE_SINGLE_GROUP = "single_group"
    MODE_GROUPED_ZIP = "grouped_zip"
    MODE_ALL_PRODUCTS = "all_products"

    mode = forms.ChoiceField(
        label="Режим экспорта",
        choices=(
            (MODE_SINGLE_GROUP, "Одна категория в XLSX"),
            (MODE_GROUPED_ZIP, "Все категории отдельными XLSX в ZIP"),
            (MODE_ALL_PRODUCTS, "Все товары в одном XLSX"),
        ),
        initial=MODE_SINGLE_GROUP,
    )
    group = forms.ModelChoiceField(
        queryset=Group.objects.order_by("name"),
        required=False,
        label="Категория",
        help_text="Используется только для режима экспорта одной категории.",
    )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("mode") == self.MODE_SINGLE_GROUP and not cleaned_data.get("group"):
            self.add_error("group", "Выберите категорию для экспорта одной таблицы.")
        return cleaned_data


class SynonymListField(forms.JSONField):
    widget = forms.Textarea

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("required", False)
        kwargs.setdefault("help_text", "Один синоним на строку. Значения сохраняются как JSON-список.")
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
            raise ValidationError("Введите список синонимов.")
        return [str(item).strip() for item in parsed if str(item).strip()]


class BrandAdminForm(AdminMediaFormMixin):
    media_field_name = "media"
    upload_folder_name = "brands"
    search_synonyms = SynonymListField(label="Поисковые синонимы", required=False)

    class Meta:
        model = Brand
        fields = "__all__"


class GroupAdminForm(SeoFieldsAdminFormMixin, AdminMediaFormMixin):
    media_field_name = "media"
    upload_folder_name = "groups"
    search_synonyms = SynonymListField(label="Поисковые синонимы", required=False)
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
        self.fields["group"].label = "Категория"
        self.fields["brand"].label = "Бренд"
        self.fields["shared_gallery"].label = "Общая галерея"
        self.fields["shared_gallery"].help_text = (
            "Выберите общую галерею, если нужно добавить одинаковые изображения "
            "сразу для группы похожих товаров."
        )
        self.fields["search_tsv"].label = "Поисковые синонимы"
        self.fields["search_tsv"].help_text = (
            "Синонимы и поисковые подсказки через запятую. "
            "Например: огнезащита, огнезащитный материал, fireproof, теплоизоляция."
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
                self.fields["characteristic"].queryset = Characteristic.objects.filter(
                    group=selected_product.group
                ).order_by("name", "id")


class CharacteristicInlineAdminForm(forms.ModelForm):
    class Meta:
        model = Characteristic
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        group = self.initial.get("group") or getattr(self.instance, "group", None)
        group_field = self.fields.get("group")
        if group_field is not None:
            if group:
                group_field.initial = getattr(group, "pk", group)
            group_field.widget = forms.HiddenInput()

        slug_field = self.fields.get("slug")
        if slug_field is not None:
            slug_field.required = False
            slug_field.help_text = "Можно оставить пустым, slug соберётся из названия автоматически."

    def clean_slug(self):
        slug = str(self.cleaned_data.get("slug") or "").strip()
        if slug:
            return slug
        name = str(self.cleaned_data.get("name") or "").strip()
        return transliterate_slug(name) if name else ""
