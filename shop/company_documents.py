from pathlib import Path
from uuid import uuid4
from zipfile import BadZipFile, ZipFile

from django.core.exceptions import ValidationError


def company_document_path(instance, filename):
    # Separate from the gallery cleanup area; never overwrite an existing file.
    return f"company_documents/{uuid4().hex}{Path(filename).suffix.lower()}"


def validate_company_document(upload):
    if upload.size > 10 * 1024 * 1024:
        raise ValidationError("Размер файла не должен превышать 10 МБ.")
    suffix = Path(upload.name).suffix.lower()
    position = upload.tell()
    try:
        upload.seek(0)
        header = upload.read(8)
        valid = suffix == ".pdf" and header.startswith(b"%PDF-")
        valid |= suffix == ".doc" and header == bytes.fromhex("d0cf11e0a1b11ae1")
        if suffix == ".docx":
            upload.seek(0)
            try:
                with ZipFile(upload) as archive:
                    names = set(archive.namelist())
                    valid = {"[Content_Types].xml", "word/document.xml"} <= names
                    valid &= not any("vbaproject" in name.lower() for name in names)
            except BadZipFile:
                valid = False
        if not valid:
            raise ValidationError("Загрузите документ PDF, DOC или DOCX. Тип файла должен соответствовать расширению.")
    finally:
        upload.seek(position)
