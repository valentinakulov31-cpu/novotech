import mimetypes
import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError


def save_admin_upload(upload, folder_name: str) -> dict:
    media_root = Path(settings.MEDIA_ROOT)
    target_dir = media_root / "admin_uploads" / folder_name
    target_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(upload.name).suffix
    filename = f"{uuid.uuid4().hex}{suffix}"
    storage_path = target_dir / filename

    with storage_path.open("wb+") as destination:
        for chunk in upload.chunks():
            destination.write(chunk)

    relative_path = storage_path.relative_to(media_root).as_posix()
    url = f"{settings.MEDIA_URL}{relative_path}"
    mime_type = upload.content_type or mimetypes.guess_type(upload.name)[0] or "application/octet-stream"

    return {
        "storage_path": str(storage_path),
        "url": url,
        "mime_type": mime_type,
        "size_bytes": upload.size,
    }


def validate_new_file_upload(form, upload_field_name: str):
    if not getattr(form, "cleaned_data", None):
        return
    if not form.has_changed():
        return
    if form.instance.pk:
        return
    if form.cleaned_data.get(upload_field_name):
        return
    raise ValidationError({upload_field_name: "Upload a file before saving this item."})


def mark_generated_file_fields_optional(form, extra_fields=None):
    optional_fields = ["storage_path", "url", "mime_type", "size_bytes"]
    if extra_fields:
        optional_fields.extend(extra_fields)
    for field_name in optional_fields:
        if field_name in form.fields:
            form.fields[field_name].required = False
