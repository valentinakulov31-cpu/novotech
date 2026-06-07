from __future__ import annotations

from redis import Redis

from django.conf import settings


def get_import_queue_name() -> str:
    return settings.CATALOG_IMPORT_QUEUE_NAME


def get_redis_client() -> Redis:
    return Redis.from_url(settings.REDIS_URL, decode_responses=True)


def enqueue_catalog_import_job(job_id: int) -> None:
    get_redis_client().lpush(get_import_queue_name(), str(job_id))

