from collections import Counter
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from shop.services.south_meridian.client import SourceClient
from shop.services.south_meridian.crawler import crawl_catalogue
from shop.services.south_meridian.workbook import write_report, write_workbook


class Command(BaseCommand):
    help = "Собрать все категории south-meridian.ru в XLSX нашего импорта, без изменения БД."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--output", default="artifacts/south-meridian/products.xlsx")
        parser.add_argument("--cache-dir")
        parser.add_argument("--delay", type=float, default=0.25)
        parser.add_argument("--timeout", type=float, default=20)
        parser.add_argument("--refresh", action="store_true", help="Повторно загрузить HTML вместо кеша")
        parser.add_argument("--skip-media-check", action="store_true", help="Не проверять доступность файлов (отладка)")
        parser.add_argument("--brand", default="SAMSUN MAKINA (SMS)")
        parser.add_argument("--publish", action="store_true", help="is_hidden=false для позиций без замечаний")

    def handle(self, *args, **options):
        output = Path(options["output"]).resolve()
        if output.suffix.lower() != ".xlsx":
            raise CommandError("--output должен иметь расширение .xlsx")
        report = output.with_suffix(".report.json")
        try:
            client = SourceClient(options["cache_dir"] or output.parent / "cache",
                                  delay=options["delay"], timeout=options["timeout"], refresh=options["refresh"])
            catalogue = crawl_catalogue(client, check_media=not options["skip_media_check"],
                                        progress=self.stdout.write if options["verbosity"] else lambda text: None)
            write_report(catalogue, report)
            write_workbook(catalogue, output, brand=options["brand"], publish=options["publish"])
        except ValueError as exc:
            raise CommandError(f"{exc}. Отчет: {report}. Старый XLSX, если он был, не обновлен.") from exc
        counts = Counter(product.category for product in catalogue.products)
        for category, count in sorted(counts.items()):
            self.stdout.write(f"{category}: {count}")
        self.stdout.write(self.style.SUCCESS(f"Товаров: {len(catalogue.products)}. XLSX: {output}\nОтчет: {report}"))
