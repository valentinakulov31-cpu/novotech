import uuid

from django.db import models


class CatalogCacheVersion(models.Model):
    """One database token shared by all API and import worker processes."""

    token = models.UUIDField(default=uuid.uuid4, editable=False)

    class Meta:
        db_table = "catalog_cache_version"
