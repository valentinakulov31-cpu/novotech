import uuid

from shop.models_cache import CatalogCacheVersion


def catalog_cache_version():
    return CatalogCacheVersion.objects.filter(pk=1).values_list("token", flat=True).first() or "initial"


def invalidate_catalog_cache(*, using="default"):
    versions = CatalogCacheVersion.objects.using(using)
    token = uuid.uuid4()
    if not versions.filter(pk=1).update(token=token):
        versions.get_or_create(pk=1, defaults={"token": token})


def catalog_changed(sender, *, using, raw=False, created=False, **kwargs):
    # Keep the cached random selection stable when new items are added.
    # Edits and deletions must invalidate payloads in every web worker.
    if not raw and not created:
        invalidate_catalog_cache(using=using)
