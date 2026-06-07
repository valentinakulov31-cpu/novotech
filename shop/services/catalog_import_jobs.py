from __future__ import annotations

import traceback
from pathlib import Path

from django.conf import settings
from django.core.files.base import File
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone

from shop.models import CatalogImportJob
from shop.services import catalog_import as catalog_import_service
from shop.services import import_queue as import_queue_service


def create_catalog_import_job(uploaded_file, *, created_by=None) -> CatalogImportJob:
    job = CatalogImportJob(
        original_filename=Path(uploaded_file.name).name,
        created_by=created_by if getattr(created_by, "is_authenticated", False) else None,
        queue_name=import_queue_service.get_import_queue_name(),
        status=CatalogImportJob.STATUS_QUEUED,
    )
    job.source_file.save(job.original_filename, File(uploaded_file), save=False)
    job.save()
    try:
        import_queue_service.enqueue_catalog_import_job(job.pk)
    except Exception as exc:  # noqa: BLE001
        job.status = CatalogImportJob.STATUS_FAILED
        job.finished_at = timezone.now()
        job.fatal_error = f"Не удалось поставить импорт в очередь: {exc}"
        job.save(update_fields=["status", "finished_at", "fatal_error"])
        raise
    return job


def process_catalog_import_job(job_id: int) -> CatalogImportJob:
    with transaction.atomic():
        job = CatalogImportJob.objects.select_for_update().get(pk=job_id)
        job.status = CatalogImportJob.STATUS_PROCESSING
        job.started_at = timezone.now()
        job.finished_at = None
        job.fatal_error = ""
        job.counters = {}
        job.issues = []
        job.save(
            update_fields=[
                "status",
                "started_at",
                "finished_at",
                "fatal_error",
                "counters",
                "issues",
            ]
        )

    try:
        with job.source_file.open("rb") as source_file:
            counters, issues = catalog_import_service.import_products_from_workbook(source_file)
    except Exception as exc:  # noqa: BLE001
        job.status = CatalogImportJob.STATUS_FAILED
        job.finished_at = timezone.now()
        job.fatal_error = "".join(traceback.format_exception_only(type(exc), exc)).strip() or str(exc)
        job.save(update_fields=["status", "finished_at", "fatal_error"])
        return job

    job.status = CatalogImportJob.STATUS_SUCCEEDED
    job.finished_at = timezone.now()
    job.counters = counters
    job.issues = issues
    job.fatal_error = ""
    job.save(update_fields=["status", "finished_at", "counters", "issues", "fatal_error"])
    return job


def build_catalog_import_report(job: CatalogImportJob) -> bytes:
    return catalog_import_service.workbook_bytes_from_import_report(job.counters or {}, job.issues or [])


def get_catalog_import_refresh_seconds(job: CatalogImportJob) -> int:
    if job.status in {CatalogImportJob.STATUS_QUEUED, CatalogImportJob.STATUS_PROCESSING}:
        return max(3, settings.CATALOG_IMPORT_QUEUE_BLOCK_SECONDS)
    return 0


def cleanup_catalog_import_job_file(job: CatalogImportJob) -> None:
    if job.source_file:
        storage_name = job.source_file.name
        job.source_file.delete(save=False)
        if storage_name and default_storage.exists(storage_name):
            default_storage.delete(storage_name)
