from django.conf import settings
from django.db import models
from django.utils import timezone

from shop.model_constants import PUBLISH_STATUS_CHOICES, PUBLISH_STATUS_DRAFT, PUBLISH_STATUS_PUBLISHED
from shop.model_utils import assign_sort_order


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
        verbose_name = "Новость"
        verbose_name_plural = "Новости"
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
        verbose_name = "Файл новости"
        verbose_name_plural = "Файлы новостей"

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
        verbose_name = "Общий сертификат"
        verbose_name_plural = "Общие сертификаты"

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
        verbose_name = "Слайд"
        verbose_name_plural = "Слайды"

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
        verbose_name = "Заявка"
        verbose_name_plural = "Заявки"

    def __str__(self):
        return f"{self.name} ({self.phone})"


class HtmlContent(models.Model):
    """Editable HTML blocks for the website."""

    title = models.CharField(max_length=255, default="Реквизиты компании")
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
        verbose_name = "Реквизиты компании"
        verbose_name_plural = "Реквизиты компании"

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
        verbose_name = "Контактная информация"
        verbose_name_plural = "Контактная информация"

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
        verbose_name = "Менеджер"
        verbose_name_plural = "Менеджеры"

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):
        assign_sort_order(self)
        super().save(*args, **kwargs)

    @property
    def is_active(self):
        return self.status == PUBLISH_STATUS_PUBLISHED
