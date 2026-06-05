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
