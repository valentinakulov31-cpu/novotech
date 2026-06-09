from django.core.management.base import BaseCommand
from django.db import transaction

from shop.model_utils import transliterate_slug
from shop.models import Characteristic, ProductCharacteristic


class Command(BaseCommand):
    help = "Remove duplicated 'char ' prefix from imported characteristic names and slugs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be changed without writing to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        renamed = 0
        merged = 0
        skipped = 0

        queryset = Characteristic.objects.filter(name__istartswith="char ").order_by("id")
        for characteristic in queryset:
            clean_name = characteristic.name[5:].strip()
            if not clean_name:
                skipped += 1
                continue

            clean_slug = transliterate_slug(clean_name)
            duplicate = (
                Characteristic.objects.filter(group=characteristic.group, slug=clean_slug)
                .exclude(pk=characteristic.pk)
                .first()
            )

            if dry_run:
                action = "merge" if duplicate else "rename"
                self.stdout.write(
                    f"{action}: #{characteristic.pk} {characteristic.name!r} -> {clean_name!r} ({clean_slug})"
                )
                if duplicate:
                    self.stdout.write(f"  duplicate target: #{duplicate.pk} {duplicate.name!r}")
                continue

            with transaction.atomic():
                if duplicate:
                    values = list(ProductCharacteristic.objects.filter(characteristic=characteristic))
                    for value in values:
                        target, created = ProductCharacteristic.objects.get_or_create(
                            product=value.product,
                            characteristic=duplicate,
                            defaults={"value": value.value},
                        )
                        if not created and target.value in (None, "") and value.value not in (None, ""):
                            target.value = value.value
                            target.save(update_fields=["value"])
                        value.delete()
                    characteristic.delete()
                    merged += 1
                else:
                    characteristic.name = clean_name
                    characteristic.slug = clean_slug
                    characteristic.save(update_fields=["name", "slug", "search_index"])
                    renamed += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. renamed={renamed}, merged={merged}, skipped={skipped}, dry_run={dry_run}"
            )
        )
