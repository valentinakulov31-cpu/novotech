from django.conf import settings
from django.db import models
from django.utils import timezone
import re
import uuid


PUBLISH_STATUS_DRAFT = "draft"
PUBLISH_STATUS_PUBLISHED = "published"
PUBLISH_STATUS_CHOICES = [
    (PUBLISH_STATUS_DRAFT, "Draft"),
    (PUBLISH_STATUS_PUBLISHED, "Published"),
]
EMAIL_NOTIFICATION_TYPE_ORDER = "order"
EMAIL_NOTIFICATION_TYPE_INQUIRY = "inquiry"
EMAIL_NOTIFICATION_TYPE_CHOICES = [
    (EMAIL_NOTIFICATION_TYPE_ORDER, "Order"),
    (EMAIL_NOTIFICATION_TYPE_INQUIRY, "Inquiry"),
]

CHARACTERISTIC_TYPE_TEXT = "text"
CHARACTERISTIC_TYPE_NUMBER = "number"
CHARACTERISTIC_TYPE_BOOLEAN = "boolean"
CHARACTERISTIC_TYPE_CHOICES = [
    (CHARACTERISTIC_TYPE_TEXT, "Text"),
    (CHARACTERISTIC_TYPE_NUMBER, "Number"),
    (CHARACTERISTIC_TYPE_BOOLEAN, "Boolean"),
]


CYRILLIC_TO_LATIN = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}

SEARCH_WORD_RE = re.compile(r"[0-9A-Za-z\u0400-\u04ff]+")
SEARCH_TYPO_TRANSLATION = str.maketrans(
    {
        "\u0451": "\u0435",
        "\u043e": "\u0430",
        "\u044b": "\u0438",
        "\u044d": "\u0435",
        "\u0439": "\u0438",
    }
)


def normalize_search_token(value: str) -> str:
    token = str(value or "").strip().lower()
    token = re.sub(r"[^0-9a-z\u0400-\u04ff]+", "", token)
    return token.translate(SEARCH_TYPO_TRANSLATION)


def transliterate_slug(value: str) -> str:
    normalized = str(value or "").strip().lower()
    transliterated = "".join(CYRILLIC_TO_LATIN.get(char, char) for char in normalized)
    transliterated = transliterated.replace("&", " and ")
    transliterated = re.sub(r"[^a-z0-9]+", "-", transliterated)
    transliterated = re.sub(r"-{2,}", "-", transliterated).strip("-")
    return transliterated or f"item-{uuid.uuid4().hex[:8]}"


def unique_product_slug(instance, base_value: str) -> str:
    base_slug = transliterate_slug(base_value)[:220].strip("-") or f"product-{uuid.uuid4().hex[:8]}"
    slug = base_slug
    index = 2
    queryset = instance.__class__.objects.filter(slug=slug)
    if instance.pk:
        queryset = queryset.exclude(pk=instance.pk)
    while queryset.exists():
        suffix = f"-{index}"
        slug = f"{base_slug[:255 - len(suffix)]}{suffix}"
        queryset = instance.__class__.objects.filter(slug=slug)
        if instance.pk:
            queryset = queryset.exclude(pk=instance.pk)
        index += 1
    return slug


def next_sort_order(model_class, filters=None) -> int:
    queryset = model_class.objects.all()
    if filters:
        queryset = queryset.filter(**filters)
    return queryset.count() + 1


def assign_sort_order(instance, filters=None):
    if not instance.pk and not instance.sort_order:
        instance.sort_order = next_sort_order(instance.__class__, filters=filters)


def include_update_fields(kwargs, *field_names):
    update_fields = kwargs.get("update_fields")
    if update_fields is not None:
        kwargs["update_fields"] = set(update_fields).union(field_names)


def normalize_synonyms(value):
    if not value:
        return []
    if isinstance(value, str):
        value = [value]
    result = []
    seen = set()
    for item in value:
        text = str(item or "").strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(text)
    return result


def search_text_parts(*values):
    parts = []
    for value in values:
        if value in (None, ""):
            continue
        if isinstance(value, (list, tuple, set)):
            parts.extend(search_text_parts(*value))
            continue
        text = str(value).strip()
        if not text:
            continue
        parts.append(text)
        transliterated = transliterate_slug(text).replace("-", " ").strip()
        if transliterated and transliterated.lower() != text.lower():
            parts.append(transliterated)
        for word in SEARCH_WORD_RE.findall(text):
            if len(word) < 5:
                continue
            normalized_word = normalize_search_token(word)
            if normalized_word and normalized_word != word.lower():
                parts.append(normalized_word)
    return parts


def build_search_index(*values):
    parts = search_text_parts(*values)
    seen = set()
    result = []
    for part in parts:
        normalized = " ".join(str(part).lower().split())
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return " ".join(result)


class Brand(models.Model):
    """Product brands."""

    name = models.CharField(max_length=255)
    slug = models.CharField(max_length=255, unique=True, blank=True, null=True)
    search_synonyms = models.JSONField(default=list, blank=True)
    search_index = models.TextField(default="", blank=True)
    media = models.CharField(max_length=1024, null=True, blank=True)

    class Meta:
        db_table = "brands"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        synonyms = normalize_synonyms(self.search_synonyms)
        transliterated = transliterate_slug(self.name).replace("-", " ")
        if transliterated and transliterated.lower() != str(self.name or "").strip().lower():
            synonyms = normalize_synonyms([*synonyms, transliterated, *transliterated.split()])
        self.search_synonyms = synonyms
        self.search_index = build_search_index(self.name, self.slug, self.search_synonyms)
        include_update_fields(kwargs, "search_synonyms", "search_index")
        super().save(*args, **kwargs)


class City(models.Model):
    """SEO city dictionary for geo pages."""

    name = models.CharField(max_length=255)
    slug = models.CharField(max_length=255, unique=True)
    name_in_prepositional = models.CharField(max_length=255, blank=True, null=True)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "cities"
        ordering = ["sort_order", "name", "id"]
        verbose_name = "City"
        verbose_name_plural = "Cities"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        assign_sort_order(self)
        super().save(*args, **kwargs)


class Group(models.Model):
    """Product groups/categories."""

    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    name = models.CharField(max_length=255)
    slug = models.CharField(max_length=255, unique=True)
    search_synonyms = models.JSONField(default=list, blank=True)
    search_index = models.TextField(default="", blank=True)
    description = models.TextField(null=True, blank=True)
    media = models.CharField(max_length=1024, null=True, blank=True)
    seo_title = models.CharField(max_length=255, null=True, blank=True)
    seo_h1 = models.CharField(max_length=255, null=True, blank=True)
    seo_description = models.TextField(null=True, blank=True)
    seo_keywords = models.TextField(null=True, blank=True)
    seo_canonical_url = models.CharField(max_length=1024, null=True, blank=True)
    seo_robots = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "groups"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.search_synonyms = normalize_synonyms(self.search_synonyms)
        self.search_index = build_search_index(self.name, self.slug, self.description, self.search_synonyms)
        include_update_fields(kwargs, "search_synonyms", "search_index")
        super().save(*args, **kwargs)


class Product(models.Model):
    """Catalog products."""

    sku = models.CharField(max_length=255, unique=True)
    slug = models.CharField(max_length=255, unique=True, blank=True)
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10)
    description = models.TextField(null=True, blank=True)
    assortment_html = models.TextField(null=True, blank=True)
    characteristics_html = models.TextField(null=True, blank=True)
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")
    media = models.JSONField(null=True, blank=True)
    available = models.BooleanField(default=True)
    search_tsv = models.TextField("Search synonyms", null=True, blank=True)
    search_index = models.TextField(default="", blank=True)
    seo_title = models.CharField(max_length=255, null=True, blank=True)
    seo_h1 = models.CharField(max_length=255, null=True, blank=True)
    seo_description = models.TextField(null=True, blank=True)
    seo_keywords = models.TextField(null=True, blank=True)
    seo_canonical_url = models.CharField(max_length=1024, null=True, blank=True)
    seo_robots = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "products"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_product_slug(self, self.name or self.sku)
        else:
            self.slug = unique_product_slug(self, self.slug)
        characteristic_values = []
        if self.pk:
            characteristic_values = list(
                self.characteristics.select_related("characteristic").values_list(
                    "value",
                    "characteristic__name",
                    "characteristic__slug",
                )
            )
        self.search_index = build_search_index(
            self.sku,
            self.slug,
            self.name,
            self.description,
            self.characteristics_html,
            self.search_tsv,
            self.brand.name if self.brand else "",
            self.brand.slug if self.brand else "",
            self.brand.search_synonyms if self.brand else [],
            self.group.name if self.group else "",
            self.group.slug if self.group else "",
            self.group.search_synonyms if self.group else [],
            characteristic_values,
        )
        include_update_fields(kwargs, "slug", "search_index")
        super().save(*args, **kwargs)


class ProductMedia(models.Model):
    """Product preview media."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="media_files")
    storage_path = models.CharField(max_length=1024)
    url = models.CharField(max_length=1024)
    mime_type = models.CharField(max_length=255)
    media_kind = models.CharField(max_length=50, default="image")
    size_bytes = models.IntegerField()
    variants = models.JSONField(null=True, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)
    alt_text = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "product_media"
        ordering = ["-is_primary", "sort_order", "id"]

    def __str__(self):
        return f"Media for {self.product.name}"

    def save(self, *args, **kwargs):
        assign_sort_order(self, filters={"product": self.product})
        super().save(*args, **kwargs)


class MediaLibrary(ProductMedia):
    class Meta:
        proxy = True
        verbose_name = "Media library"
        verbose_name_plural = "Media library"


class ProductGalleryItem(models.Model):
    """Full gallery files for product pages."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="gallery_items")
    storage_path = models.CharField(max_length=1024)
    url = models.CharField(max_length=1024)
    mime_type = models.CharField(max_length=255)
    file_kind = models.CharField(max_length=50, default="image")
    size_bytes = models.IntegerField()
    sort_order = models.IntegerField(default=0)
    title = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "product_gallery_items"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"Gallery item for {self.product.name}"

    def save(self, *args, **kwargs):
        assign_sort_order(self, filters={"product": self.product})
        super().save(*args, **kwargs)


class ProductCertificate(models.Model):
    """Certificates attached to a product."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="certificates")
    title = models.CharField(max_length=255)
    storage_path = models.CharField(max_length=1024)
    url = models.CharField(max_length=1024)
    mime_type = models.CharField(max_length=255)
    size_bytes = models.IntegerField()
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "product_certificates"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.title} for {self.product.name}"

    def save(self, *args, **kwargs):
        assign_sort_order(self, filters={"product": self.product})
        super().save(*args, **kwargs)


class Characteristic(models.Model):
    """Characteristic definitions (EAV)."""

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="characteristics")
    name = models.CharField(max_length=255)
    slug = models.CharField(max_length=255, default="")
    data_type = models.CharField(max_length=50, choices=CHARACTERISTIC_TYPE_CHOICES, default=CHARACTERISTIC_TYPE_TEXT)
    unit = models.CharField(max_length=50, null=True, blank=True)
    search_index = models.TextField(default="", blank=True)
    is_filterable = models.BooleanField(default=True)
    is_searchable = models.BooleanField(default=False)

    class Meta:
        db_table = "characteristics"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.search_index = build_search_index(
            self.name,
            self.slug,
            self.unit,
            self.group.name if self.group else "",
            self.group.slug if self.group else "",
        )
        include_update_fields(kwargs, "search_index")
        super().save(*args, **kwargs)


class ProductCharacteristic(models.Model):
    """Characteristic values for products (EAV)."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="characteristics")
    characteristic = models.ForeignKey(Characteristic, on_delete=models.CASCADE)
    value = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "product_characteristics"

    def __str__(self):
        return f"{self.product.name} - {self.characteristic.name}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.product_id:
            self.product.save(update_fields=["search_index"])

    def delete(self, *args, **kwargs):
        product = self.product
        result = super().delete(*args, **kwargs)
        product.save(update_fields=["search_index"])
        return result


class News(models.Model):
    """News posts."""

    title = models.CharField(max_length=255)
    slug = models.CharField(max_length=255, unique=True)
    content = models.TextField()
    media = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=PUBLISH_STATUS_CHOICES, default=PUBLISH_STATUS_DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        db_table = "news"
        verbose_name_plural = "News"
        ordering = ["-published_at", "-updated_at", "-id"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.slug = (self.slug or "").strip() or None
        super().save(*args, **kwargs)

    @property
    def is_published(self):
        return self.status == PUBLISH_STATUS_PUBLISHED


class NewsAttachment(models.Model):
    """Files attached to news."""

    news = models.ForeignKey(News, on_delete=models.CASCADE, related_name="attachments")
    title = models.CharField(max_length=255)
    storage_path = models.CharField(max_length=1024)
    url = models.CharField(max_length=1024)
    mime_type = models.CharField(max_length=255)
    size_bytes = models.IntegerField()
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "news_attachments"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.title} for {self.news.title}"

    def save(self, *args, **kwargs):
        assign_sort_order(self, filters={"news": self.news})
        super().save(*args, **kwargs)


class Sert(models.Model):
    """Global certificates/documents."""

    title = models.CharField(max_length=255)
    storage_path = models.CharField(max_length=1024)
    url = models.CharField(max_length=1024)
    mime_type = models.CharField(max_length=255)
    size_bytes = models.IntegerField()
    sort_order = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=PUBLISH_STATUS_CHOICES, default=PUBLISH_STATUS_DRAFT)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        db_table = "serts"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        assign_sort_order(self)
        super().save(*args, **kwargs)

    @property
    def is_active(self):
        return self.status == PUBLISH_STATUS_PUBLISHED


class Slider(models.Model):
    """Homepage slider items."""

    image = models.CharField(max_length=1024)
    title = models.CharField(max_length=255)
    text = models.TextField(blank=True, null=True)
    slug = models.CharField(max_length=255, unique=True, blank=True, null=True)
    sort_order = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=PUBLISH_STATUS_CHOICES, default=PUBLISH_STATUS_DRAFT)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        db_table = "sliders"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.slug = (self.slug or "").strip() or None
        assign_sort_order(self)
        super().save(*args, **kwargs)

    @property
    def is_active(self):
        return self.status == PUBLISH_STATUS_PUBLISHED


class Inquiry(models.Model):
    """Incoming website inquiries."""

    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(max_length=255, blank=True, null=True)
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "inquiries"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.name} ({self.phone})"


class HtmlContent(models.Model):
    """Editable HTML blocks for the website."""

    title = models.CharField(max_length=255, default="Main HTML content")
    html_first = models.TextField()
    html_second = models.TextField()
    status = models.CharField(max_length=20, choices=PUBLISH_STATUS_CHOICES, default=PUBLISH_STATUS_DRAFT)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        db_table = "html_content"
        ordering = ["-updated_at", "-id"]

    def __str__(self):
        return self.title

    @property
    def is_active(self):
        return self.status == PUBLISH_STATUS_PUBLISHED


class ContactInfo(models.Model):
    """Company contact details."""

    title = models.CharField(max_length=255, default="Наши контакты")
    full_name = models.CharField(max_length=255, blank=True, null=True)
    address = models.TextField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    yandex_link = models.URLField(max_length=1024, blank=True, null=True)
    gis_link = models.URLField(max_length=1024, blank=True, null=True)
    schedule = models.TextField()
    phone = models.CharField(max_length=100)
    email = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=PUBLISH_STATUS_CHOICES, default=PUBLISH_STATUS_DRAFT)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        db_table = "contact_info"
        ordering = ["-updated_at", "-id"]
        verbose_name = "Contact info"
        verbose_name_plural = "Contact info"

    def __str__(self):
        return self.title

    @property
    def is_active(self):
        return self.status == PUBLISH_STATUS_PUBLISHED


class Agent(models.Model):
    """Sales/contact agent displayed on the public contacts block."""

    full_name = models.CharField(max_length=255)
    position = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    phone = models.CharField(max_length=100)
    sort_order = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=PUBLISH_STATUS_CHOICES, default=PUBLISH_STATUS_DRAFT)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        db_table = "agents"
        ordering = ["sort_order", "id"]
        verbose_name = "Agent"
        verbose_name_plural = "Agents"

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):
        assign_sort_order(self)
        super().save(*args, **kwargs)

    @property
    def is_active(self):
        return self.status == PUBLISH_STATUS_PUBLISHED


class PublicOrder(models.Model):
    """Orders submitted from the website."""

    STATUS_NEW = "new"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_DONE = "done"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_NEW, "New"),
        (STATUS_IN_PROGRESS, "In progress"),
        (STATUS_DONE, "Done"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50)
    email = models.EmailField(max_length=255, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default=STATUS_NEW)
    total_items = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "public_orders"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"Order #{self.id} - {self.name}"


class PublicOrderItem(models.Model):
    """Items inside a public order."""

    order = models.ForeignKey(PublicOrder, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="public_order_items")
    qty = models.PositiveIntegerField()

    class Meta:
        db_table = "public_order_items"
        ordering = ["id"]

    def __str__(self):
        return f"{self.product.name} x {self.qty}"


class OrderEmailRecipient(models.Model):
    """Recipients for website email notifications."""

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "order_email_recipients"
        ordering = ["email"]
        verbose_name = "Email recipient"
        verbose_name_plural = "Email recipients"

    def __str__(self):
        return self.email


class OrderEmailSettings(models.Model):
    """Settings for website email notifications."""

    title = models.CharField(max_length=255, default="Order email settings")
    notification_type = models.CharField(
        max_length=20,
        choices=EMAIL_NOTIFICATION_TYPE_CHOICES,
        default=EMAIL_NOTIFICATION_TYPE_ORDER,
    )
    subject = models.CharField(max_length=255, default="Заказ #{{order_id}} от {{name}} {{phone}}")
    intro_html = models.TextField(blank=True, null=True)
    body_html = models.TextField(blank=True, null=True)
    footer_html = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=PUBLISH_STATUS_CHOICES, default=PUBLISH_STATUS_DRAFT)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        db_table = "order_email_settings"
        ordering = ["-updated_at", "-id"]
        verbose_name = "Email template"
        verbose_name_plural = "Email templates"

    def __str__(self):
        return self.title

    @property
    def is_active(self):
        return self.status == PUBLISH_STATUS_PUBLISHED
