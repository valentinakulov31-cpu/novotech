from django.conf import settings
from django.db import models
from django.utils import timezone


PUBLISH_STATUS_DRAFT = "draft"
PUBLISH_STATUS_PUBLISHED = "published"
PUBLISH_STATUS_CHOICES = [
    (PUBLISH_STATUS_DRAFT, "Draft"),
    (PUBLISH_STATUS_PUBLISHED, "Published"),
]


class Brand(models.Model):
    """Product brands."""

    name = models.CharField(max_length=255)
    slug = models.CharField(max_length=255, unique=True)
    media = models.CharField(max_length=1024, null=True, blank=True)

    class Meta:
        db_table = "brands"

    def __str__(self):
        return self.name


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


class Product(models.Model):
    """Catalog products."""

    sku = models.CharField(max_length=255, unique=True)
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


class ProductDocument(models.Model):
    """Documents attached to a product."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=255)
    storage_path = models.CharField(max_length=1024)
    url = models.CharField(max_length=1024)
    mime_type = models.CharField(max_length=255)
    size_bytes = models.IntegerField()
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "product_documents"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.title} for {self.product.name}"


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


class Characteristic(models.Model):
    """Characteristic definitions (EAV)."""

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="characteristics")
    name = models.CharField(max_length=255)
    slug = models.CharField(max_length=255, default="")
    data_type = models.CharField(max_length=50, default="text")
    unit = models.CharField(max_length=50, null=True, blank=True)
    is_filterable = models.BooleanField(default=True)
    is_searchable = models.BooleanField(default=False)

    class Meta:
        db_table = "characteristics"

    def __str__(self):
        return self.name


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

    @property
    def is_active(self):
        return self.status == PUBLISH_STATUS_PUBLISHED


class Slider(models.Model):
    """Homepage slider items."""

    image = models.CharField(max_length=1024)
    title = models.CharField(max_length=255)
    text = models.TextField(blank=True, null=True)
    slug = models.CharField(max_length=255, unique=True)
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
    """Recipients for public order email notifications."""

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "order_email_recipients"
        ordering = ["email"]
        verbose_name = "Order email recipient"
        verbose_name_plural = "Order email recipients"

    def __str__(self):
        return self.email


class OrderEmailSettings(models.Model):
    """Settings for new order email notifications."""

    title = models.CharField(max_length=255, default="Order email settings")
    subject = models.CharField(max_length=255, default="Новый заказ с сайта")
    intro_html = models.TextField(blank=True, null=True)
    footer_html = models.TextField(blank=True, null=True)
    from_email = models.EmailField(blank=True, null=True)
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
        verbose_name = "Order email settings"
        verbose_name_plural = "Order email settings"

    def __str__(self):
        return self.title

    @property
    def is_active(self):
        return self.status == PUBLISH_STATUS_PUBLISHED
