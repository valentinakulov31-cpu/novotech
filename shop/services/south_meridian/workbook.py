import json
from dataclasses import asdict
from pathlib import Path

from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Alignment, Font, PatternFill


HEADERS = [
    "sku", "slug", "name", "group_slug", "brand_slug", "price", "currency", "available", "is_hidden",
    "description", "characteristics_html", "media_urls", "gallery_urls", "gallery_titles",
    "certificate_urls", "certificate_titles", "seo_title", "seo_h1", "seo_description", "seo_robots",
    "source_url", "source_key", "parser_warnings",
]


def file_titles(assets):
    # The legacy importer treats commas/semicolons as title separators.
    return "\n".join(asset.title.replace(",", " ").replace(";", " ")[:255] for asset in assets)


def product_row(product, *, brand, publish):
    photos = [asset for asset in product.assets if asset.kind == "image"]
    certificates = [asset for asset in product.assets if asset.kind == "document"
                    and any(word in asset.title.lower() for word in ("сертификат", "certificate"))]
    gallery = [asset for asset in product.assets if asset.kind != "image" and asset not in certificates]
    return {
        "sku": product.sku, "slug": product.slug, "name": product.name,
        # The existing importer resolves these columns by name as well as slug.
        "group_slug": product.category, "brand_slug": brand, "price": 0, "currency": "RUB",
        "available": False, "is_hidden": not publish or bool(product.warnings),
        "description": product.description, "characteristics_html": product.characteristics_html,
        "media_urls": "\n".join(asset.url for asset in photos),
        "gallery_urls": "\n".join(asset.url for asset in gallery), "gallery_titles": file_titles(gallery),
        "certificate_urls": "\n".join(asset.url for asset in certificates),
        "certificate_titles": file_titles(certificates), "seo_title": product.name,
        "seo_h1": product.name, "seo_description": " ".join(product.description.split())[:300],
        "seo_robots": "index,follow", "source_url": product.source_url,
        "source_key": product.source_key, "parser_warnings": "\n".join(product.warnings),
        **{f"char_{key}": value for key, value in product.characteristics.items()},
    }


def append_row(sheet, values):
    row_number = sheet.max_row + 1 if sheet.max_row > 1 or sheet.cell(1, 1).value is not None else 1
    for column, value in enumerate(values, 1):
        if isinstance(value, str):
            if len(value) > 32767 or ILLEGAL_CHARACTERS_RE.search(value):
                raise ValueError(f"Значение не помещается в XLSX: {sheet.title}, строка {row_number}, колонка {column}. Полный текст сохранен в JSON.")
        cell = sheet.cell(row_number, column, value)
        if isinstance(value, str):
            # Source content must stay text, even when it starts with '=' or '+'.
            cell.data_type = "s"


def format_sheet(sheet):
    sheet.freeze_panes = "D2" if sheet.title == "Products" else "A2"
    sheet.auto_filter.ref = sheet.dimensions
    sheet.row_dimensions[1].height = 28
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="243B53")
        sheet.column_dimensions[cell.column_letter].width = 24
    for row in sheet.iter_rows(min_row=2):
        sheet.row_dimensions[row[0].row].height = 44
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    if sheet.title == "Products":
        sheet.column_dimensions["C"].width = 55


def write_report(catalogue, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(asdict(catalogue), ensure_ascii=False, indent=2), encoding="utf-8")


def write_workbook(catalogue, path, *, brand="SAMSUN MAKINA (SMS)", publish=False):
    if catalogue.errors:
        raise ValueError("В сборе есть ошибки; XLSX не создан, подробности в JSON-отчете")
    catalogue.validate()
    workbook = Workbook()
    products = workbook.active
    products.title = "Products"
    characteristics = sorted({f"char_{key}" for p in catalogue.products for key in p.characteristics})
    headers = HEADERS + characteristics
    append_row(products, headers)
    for product in catalogue.products:
        row = product_row(product, brand=brand, publish=publish)
        append_row(products, [row.get(header, "") for header in headers])
    sheets = [
        ("Категории", ["name", "source_url", "media_url", "source_content_html"], catalogue.categories),
        ("Документы источника", ["title", "url", "note"], catalogue.documents),
        ("Страницы", ["url", "status", "products"], catalogue.pages),
        ("Проверка файлов", ["url", "kind", "status", "mime_type", "size_bytes"], catalogue.media_checks),
        ("Замечания", ["sku", "name", "source_url", "warning"], [
            {"sku": p.sku, "name": p.name, "source_url": p.source_url, "warning": warning}
            for p in catalogue.products for warning in p.warnings
        ]),
        ("Инструкция", ["Поле", "Пояснение"], [
            {"Поле": "Импорт", "Пояснение": "Импортируется только активный лист Products; остальные листы справочные."},
            {"Поле": "Артикулы", "Пояснение": "Стабильные численные идентификаторы источника, не заводские артикулы. Повторный импорт обновляет позиции."},
            {"Поле": "Ассортимент", "Пояснение": "Источник публикует серии и типы, а не SKU всех диаметров. Варианты размеров не выдумываются."},
            {"Поле": "Цена и наличие", "Пояснение": "Источник не сообщает цены и остатки: price=0, available=false. Проверить перед публикацией."},
            {"Поле": "Видимость", "Пояснение": "По умолчанию is_hidden=true. --publish открывает только позиции без замечаний."},
            {"Поле": "Файлы", "Пояснение": "Оригинальные ссылки; существующий импорт скачивает файлы в собственное хранилище. HEAD-проверка не заменяет проверку скачивания."},
            {"Поле": "Документы", "Пояснение": "Общие папки Яндекс Диска оставлены справочно, без неподтвержденной привязки сертификатов к товарам."},
            {"Поле": "Категории", "Пояснение": "Имена групп переданы в group_slug. Фото/описания групп из справочного листа текущий импорт не загружает."},
        ]),
    ]
    for name, columns, rows in sheets:
        sheet = workbook.create_sheet(name)
        append_row(sheet, columns)
        for row in rows:
            append_row(sheet, [row.get(column, "") for column in columns])
    for sheet in workbook:
        format_sheet(sheet)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp.xlsx")
    workbook.save(temporary)
    temporary.replace(path)
