from django.conf import settings
from django.db import models
from django.utils import timezone

from shop.model_constants import (
    EMAIL_NOTIFICATION_TYPE_CHOICES,
    EMAIL_NOTIFICATION_TYPE_ORDER,
    PUBLISH_STATUS_CHOICES,
    PUBLISH_STATUS_DRAFT,
    PUBLISH_STATUS_PUBLISHED,
)
from shop.models_catalog import Product


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
