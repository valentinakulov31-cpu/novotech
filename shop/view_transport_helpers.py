from rest_framework.exceptions import ValidationError

from shop.file_utils import save_uploaded_file
from shop.seo import resolve_city


def resolve_request_city(request, query_param: str = "city_slug"):
    return resolve_city_slug(request.query_params.get(query_param))


def resolve_city_slug(city_slug):
    return resolve_city(city_slug=city_slug)


def create_instance_from_request(serializer_class, request, *, context=None):
    serializer = serializer_class(data=request.data, context=context or {})
    serializer.is_valid(raise_exception=True)
    return serializer.save()


def validate_request_data(serializer_class, request, *, context=None):
    serializer = serializer_class(data=request.data, context=context or {})
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def update_instance_from_request(instance, serializer_class, request, *, context=None):
    serializer = serializer_class(data=request.data, context=context or {})
    serializer.is_valid(raise_exception=True)
    serializer.update(instance, serializer.validated_data)
    return instance


def require_uploaded_file(request, field_name: str = "file"):
    upload = request.FILES.get(field_name)
    if not upload:
        raise ValidationError({field_name: "No file provided"})
    return upload


def update_instance_file_field(instance, upload, folder_name: str, *, field_name: str = "media", save_fields=None):
    uploaded = save_uploaded_file(upload, folder_name)
    setattr(instance, field_name, uploaded["url"])
    if save_fields is None:
        save_fields = [field_name]
    instance.save(update_fields=save_fields)
    return instance
