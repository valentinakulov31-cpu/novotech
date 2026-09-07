import json
import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from shop.catalog_cache import invalidate_catalog_cache
from shop.models import Group, Product


SEO_FIELDS = ("seo_title", "seo_h1", "seo_description", "seo_keywords", "seo_canonical_url")


class Command(BaseCommand):
    help = "Reset catalog SEO overrides with an exclusive backup; preview by default. Content and robots are preserved."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--backup", type=Path)

    def handle(self, *args, **options):
        backup = options["backup"]
        if options["apply"] and not backup:
            raise CommandError("--apply requires --backup outside public media/static directories.")
        if backup:
            backup = backup.resolve()
            for root in (settings.MEDIA_ROOT, settings.STATIC_ROOT):
                if backup.is_relative_to(Path(root).resolve()):
                    raise CommandError("Backup must not be publicly served.")

        criteria = Q()
        for field in SEO_FIELDS:
            criteria |= Q(**{f"{field}__isnull": False}) & ~Q(**{field: ""})
        with transaction.atomic():
            snapshots = {}
            for model in (Product, Group):
                query = model.objects.filter(criteria).order_by("pk")
                if options["apply"]:
                    query = query.select_for_update()
                snapshots[model._meta.label_lower] = list(
                    query.values("pk", "name", *SEO_FIELDS, "seo_robots")
                )
            counts = {name: len(rows) for name, rows in snapshots.items()}
            self.stdout.write(json.dumps({"apply": options["apply"], "counts": counts}))
            if not options["apply"] or not any(counts.values()):
                return

            # Finish and fsync the backup before modifying even one database row.
            try:
                fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump({"version": 1, "created_at": timezone.now().isoformat(),
                               "fields": SEO_FIELDS, "records": snapshots}, handle,
                              ensure_ascii=False, indent=2)
                    handle.flush()
                    os.fsync(handle.fileno())
            except OSError as exc:
                raise CommandError(f"No changes made: backup failed: {exc}") from exc

            for model in (Product, Group):
                ids = [row["pk"] for row in snapshots[model._meta.label_lower]]
                model.objects.filter(pk__in=ids).update(**dict.fromkeys(SEO_FIELDS))
            invalidate_catalog_cache()
        self.stdout.write(self.style.SUCCESS(f"SEO overrides reset. Backup: {backup}"))
