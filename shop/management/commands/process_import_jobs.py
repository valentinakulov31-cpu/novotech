from django.conf import settings
from django.core.management.base import BaseCommand

from shop.services import catalog_import_jobs as catalog_import_jobs_service
from shop.services import import_queue as import_queue_service


class Command(BaseCommand):
    help = "Process catalog import jobs from Redis queue."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Process at most one queued import job.")

    def handle(self, *args, **options):
        queue_name = import_queue_service.get_import_queue_name()
        redis_client = import_queue_service.get_redis_client()
        timeout = max(1, settings.CATALOG_IMPORT_QUEUE_BLOCK_SECONDS)
        process_once = options["once"]

        self.stdout.write(self.style.SUCCESS(f"Listening for catalog import jobs on '{queue_name}'"))
        while True:
            payload = redis_client.brpop(queue_name, timeout=timeout)
            if payload is None:
                if process_once:
                    return
                continue

            _, raw_job_id = payload
            job = catalog_import_jobs_service.process_catalog_import_job(int(raw_job_id))
            self.stdout.write(f"Processed import job #{job.pk} with status '{job.status}'")
            if process_once:
                return
