import mimetypes
import os
from datetime import datetime, timezone as tz
from pathlib import Path

from django.conf import settings


def infer_file_kind(mime_type: str) -> str:
    mime_type = mime_type or ''
    if mime_type.startswith('image/'):
        return 'image'
    if mime_type.startswith('video/'):
        return 'video'
    return 'document'


def save_uploaded_file(file, prefix: str) -> dict:
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    safe_name = Path(file.name).name
    filename = f"{prefix}_{int(datetime.now(tz.utc).timestamp())}_{safe_name}"
    storage_path = os.path.join(settings.MEDIA_ROOT, filename)

    with open(storage_path, 'wb+') as destination:
        for chunk in file.chunks():
            destination.write(chunk)

    mime_type = file.content_type or mimetypes.guess_type(safe_name)[0] or 'application/octet-stream'
    return {
        'storage_path': storage_path,
        'url': f"/static/{filename}",
        'mime_type': mime_type,
        'size_bytes': file.size,
        'file_kind': infer_file_kind(mime_type),
    }
