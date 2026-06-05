from django.db import models
from django.utils import timezone

from shop.model_constants import CHARACTERISTIC_TYPE_CHOICES
from shop.model_utils import (
    assign_sort_order,
    include_update_fields,
    prepare_brand_search_fields,
    prepare_characteristic_search_index,
    prepare_group_search_fields,
    prepare_product_search_index,
    refresh_product_search_index,
    unique_product_slug,
)


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
        self.search_synonyms, self.search_index = prepare_brand_search_fields(self)
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
        self.search_synonyms, self.search_index = prepare_group_search_fields(self)
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
        self.search_index = prepare_product_search_index(self)
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
    data_type = models.CharField(max_length=50, choices=CHARACTERISTIC_TYPE_CHOICES, default="text")
    unit = models.CharField(max_length=50, null=True, blank=True)
    search_index = models.TextField(default="", blank=True)
    is_filterable = models.BooleanField(default=True)
    is_searchable = models.BooleanField(default=False)

    class Meta:
        db_table = "characteristics"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.search_index = prepare_characteristic_search_index(self)
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
            refresh_product_search_index(self.product)

    def delete(self, *args, **kwargs):
        product = self.product
        result = super().delete(*args, **kwargs)
        refresh_product_search_index(product)
        return result
