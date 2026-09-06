from django.db import transaction

from shop.catalog_cache import invalidate_catalog_cache


def set_catalog_visibility(queryset, *, hidden):
    with transaction.atomic(using=queryset.db):
        changed = list(queryset.select_for_update().exclude(is_hidden=hidden).only("id", "name"))
        if changed:
            queryset.model.objects.using(queryset.db).filter(pk__in=[obj.pk for obj in changed]).update(is_hidden=hidden)
            invalidate_catalog_cache(using=queryset.db)
        return changed
