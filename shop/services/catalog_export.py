import json
import re
from io import BytesIO

from django.core.exceptions import ValidationError


def _load_products(products_queryset):
    return list(
        products_queryset.select_related("group", "group__parent", "brand", "shared_gallery").prefetch_related(
            "characteristics__characteristic",
            "characteristics__characteristic__group",
            "media_files",
            "gallery_items",
            "certificates",
            "shared_gallery__items",
        )
    )


def _characteristic_header(name):
    normalized = str(name or "").strip().replace("\n", " ")
    normalized = re.sub(r"\s+", "_", normalized)
    return f"char_{normalized}"


def _json_value(value):
    if value in (None, ""):
        return ""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _boolean_value(value):
    return "Да" if value else "Нет"


def _datetime_value(value):
    return value.isoformat() if value else ""


def _join_values(items, attribute):
    values = (getattr(item, attribute, None) for item in items)
    return ",".join("" if value is None else str(value) for value in values)


def _field_value(item, attribute):
    value = getattr(item, attribute, None)
    return "" if value is None else value


def _build_product_rows(products):
    characteristic_names = {
        item.characteristic.slug: item.characteristic.name
        for product in products
        for item in product.characteristics.all()
    }
    ordered_characteristics = sorted(characteristic_names.items(), key=lambda item: item[1].lower())
    headers = [
        "id",
        "sku",
        "slug",
        "name",
        "price",
        "currency",
        "description",
        "assortment_html",
        "characteristics_html",
        "search_tsv",
        "seo_title",
        "seo_h1",
        "seo_description",
        "seo_keywords",
        "seo_canonical_url",
        "seo_robots",
        "group_id",
        "group_slug",
        "group_name",
        "group_actual_slug",
        "brand_id",
        "brand_slug",
        "brand_name",
        "brand_actual_slug",
        "shared_gallery_id",
        "shared_gallery_slug",
        "shared_gallery_name",
        "shared_gallery_description",
        "available",
        "is_hidden",
        "media_json",
        "search_index",
        "media_urls",
        "media_storage_paths",
        "media_mime_types",
        "media_kinds",
        "media_size_bytes",
        "media_variants_json",
        "media_is_primary",
        "media_sort_orders",
        "media_alt_texts",
        "gallery_urls",
        "gallery_titles",
        "gallery_storage_paths",
        "gallery_mime_types",
        "gallery_file_kinds",
        "gallery_size_bytes",
        "gallery_sort_orders",
        "shared_gallery_urls",
        "shared_gallery_titles",
        "shared_gallery_storage_paths",
        "shared_gallery_mime_types",
        "shared_gallery_file_kinds",
        "shared_gallery_size_bytes",
        "shared_gallery_sort_orders",
        "certificate_urls",
        "certificate_titles",
        "certificate_storage_paths",
        "certificate_mime_types",
        "certificate_size_bytes",
        "certificate_sort_orders",
        "characteristics_json",
        *[_characteristic_header(name) for _, name in ordered_characteristics],
    ]
    rows = []
    for product in products:
        product_characteristics = list(product.characteristics.all())
        product_media = list(product.media_files.all())
        gallery_items = list(product.gallery_items.all())
        certificates = list(product.certificates.all())
        shared_gallery_items = list(product.shared_gallery.items.all()) if product.shared_gallery else []
        values_by_slug = {
            item.characteristic.slug: item.value
            for item in product_characteristics
        }
        characteristics_json = [
            {
                "id": item.id,
                "characteristic_id": item.characteristic_id,
                "name": item.characteristic.name,
                "slug": item.characteristic.slug,
                "data_type": item.characteristic.data_type,
                "unit": item.characteristic.unit,
                "is_filterable": item.characteristic.is_filterable,
                "is_searchable": item.characteristic.is_searchable,
                "value": item.value,
                "created_at": _datetime_value(item.created_at),
            }
            for item in product_characteristics
        ]
        rows.append(
            [
                product.id,
                product.sku,
                product.slug,
                product.name,
                str(product.price),
                product.currency,
                product.description or "",
                product.assortment_html or "",
                product.characteristics_html or "",
                product.search_tsv or "",
                product.seo_title or "",
                product.seo_h1 or "",
                product.seo_description or "",
                product.seo_keywords or "",
                product.seo_canonical_url or "",
                product.seo_robots or "",
                product.group_id or "",
                product.group.name if product.group else "",
                product.group.name if product.group else "",
                product.group.slug if product.group else "",
                product.brand_id or "",
                product.brand.name if product.brand else "",
                product.brand.name if product.brand else "",
                product.brand.slug if product.brand else "",
                product.shared_gallery_id or "",
                product.shared_gallery.slug if product.shared_gallery else "",
                product.shared_gallery.name if product.shared_gallery else "",
                (product.shared_gallery.description or "") if product.shared_gallery else "",
                _boolean_value(product.available),
                _boolean_value(product.is_hidden),
                _json_value(product.media),
                product.search_index or "",
                _join_values(product_media, "url")
                or ",".join(str(value) for value in (product.media or []) if value),
                _join_values(product_media, "storage_path"),
                _join_values(product_media, "mime_type"),
                _join_values(product_media, "media_kind"),
                _join_values(product_media, "size_bytes"),
                _json_value([item.variants for item in product_media]),
                ",".join(_boolean_value(item.is_primary) for item in product_media),
                _join_values(product_media, "sort_order"),
                _join_values(product_media, "alt_text"),
                _join_values(gallery_items, "url"),
                _join_values(gallery_items, "title"),
                _join_values(gallery_items, "storage_path"),
                _join_values(gallery_items, "mime_type"),
                _join_values(gallery_items, "file_kind"),
                _join_values(gallery_items, "size_bytes"),
                _join_values(gallery_items, "sort_order"),
                _join_values(shared_gallery_items, "url"),
                _join_values(shared_gallery_items, "title"),
                _join_values(shared_gallery_items, "storage_path"),
                _join_values(shared_gallery_items, "mime_type"),
                _join_values(shared_gallery_items, "file_kind"),
                _join_values(shared_gallery_items, "size_bytes"),
                _join_values(shared_gallery_items, "sort_order"),
                _join_values(certificates, "url"),
                _join_values(certificates, "title"),
                _join_values(certificates, "storage_path"),
                _join_values(certificates, "mime_type"),
                _join_values(certificates, "size_bytes"),
                _join_values(certificates, "sort_order"),
                _json_value(characteristics_json),
                *[values_by_slug.get(slug, "") or "" for slug, _ in ordered_characteristics],
            ]
        )
    return headers, rows


def build_product_export_rows(products_queryset):
    return _build_product_rows(_load_products(products_queryset))


def _file_sheet_rows(products, relation_name, field_names):
    return [
        [item.id, product.id, product.sku, product.name, *[_field_value(item, name) for name in field_names]]
        for product in products
        for item in getattr(product, relation_name).all()
    ]


def _related_sheets(products):
    groups = {product.group_id: product.group for product in products if product.group_id}
    brands = {product.brand_id: product.brand for product in products if product.brand_id}
    shared_galleries = {
        product.shared_gallery_id: product.shared_gallery
        for product in products
        if product.shared_gallery_id
    }
    product_media_rows = []
    characteristic_rows = []
    for product in products:
        for item in product.media_files.all():
            product_media_rows.append(
                [
                    item.id,
                    product.id,
                    product.sku,
                    product.name,
                    item.storage_path,
                    item.url,
                    item.mime_type,
                    item.media_kind,
                    item.size_bytes,
                    _json_value(item.variants),
                    _boolean_value(item.is_primary),
                    item.sort_order,
                    item.alt_text or "",
                ]
            )
        for item in product.characteristics.all():
            characteristic = item.characteristic
            characteristic_rows.append(
                [
                    item.id,
                    product.id,
                    product.sku,
                    product.name,
                    characteristic.id,
                    characteristic.group_id,
                    characteristic.group.slug,
                    characteristic.name,
                    characteristic.slug,
                    characteristic.data_type,
                    characteristic.unit or "",
                    characteristic.search_index or "",
                    _boolean_value(characteristic.is_filterable),
                    _boolean_value(characteristic.is_searchable),
                    item.value or "",
                    _datetime_value(item.created_at),
                ]
            )

    gallery_fields = ["storage_path", "url", "mime_type", "file_kind", "size_bytes", "sort_order", "title"]
    certificate_fields = ["title", "storage_path", "url", "mime_type", "size_bytes", "sort_order"]
    return [
        (
            "ProductMedia",
            [
                "id", "product_id", "product_sku", "product_name", "storage_path", "url", "mime_type",
                "media_kind", "size_bytes", "variants_json", "is_primary", "sort_order", "alt_text",
            ],
            product_media_rows,
        ),
        (
            "ProductGallery",
            ["id", "product_id", "product_sku", "product_name", *gallery_fields],
            _file_sheet_rows(products, "gallery_items", gallery_fields),
        ),
        (
            "Certificates",
            ["id", "product_id", "product_sku", "product_name", *certificate_fields],
            _file_sheet_rows(products, "certificates", certificate_fields),
        ),
        (
            "SharedGalleries",
            ["id", "name", "slug", "description"],
            [
                [gallery.id, gallery.name, gallery.slug, gallery.description or ""]
                for gallery in sorted(shared_galleries.values(), key=lambda item: item.id)
            ],
        ),
        (
            "SharedGalleryItems",
            ["id", "gallery_id", "gallery_slug", "gallery_name", *gallery_fields],
            [
                [item.id, gallery.id, gallery.slug, gallery.name, *[_field_value(item, name) for name in gallery_fields]]
                for gallery in shared_galleries.values()
                for item in gallery.items.all()
            ],
        ),
        (
            "Characteristics",
            [
                "id", "product_id", "product_sku", "product_name", "characteristic_id", "group_id",
                "group_slug", "name", "slug", "data_type", "unit", "search_index", "is_filterable",
                "is_searchable", "value", "created_at",
            ],
            characteristic_rows,
        ),
        (
            "Groups",
            [
                "id", "parent_id", "parent_slug", "name", "slug", "search_synonyms_json", "search_index",
                "description", "media", "seo_title", "seo_h1", "seo_description", "seo_keywords",
                "seo_canonical_url", "seo_robots",
            ],
            [
                [
                    group.id,
                    group.parent_id or "",
                    group.parent.slug if group.parent else "",
                    group.name,
                    group.slug,
                    _json_value(group.search_synonyms),
                    group.search_index or "",
                    group.description or "",
                    group.media or "",
                    group.seo_title or "",
                    group.seo_h1 or "",
                    group.seo_description or "",
                    group.seo_keywords or "",
                    group.seo_canonical_url or "",
                    group.seo_robots or "",
                ]
                for group in sorted(groups.values(), key=lambda item: item.id)
            ],
        ),
        (
            "Brands",
            ["id", "name", "slug", "search_synonyms_json", "search_index", "media", "is_hidden"],
            [
                [
                    brand.id,
                    brand.name,
                    brand.slug or "",
                    _json_value(brand.search_synonyms),
                    brand.search_index or "",
                    brand.media or "",
                    _boolean_value(brand.is_hidden),
                ]
                for brand in sorted(brands.values(), key=lambda item: item.id)
            ],
        ),
    ]


def _append_worksheet(workbook, title, headers, rows):
    from openpyxl.styles import Font

    worksheet = workbook.create_sheet(title=title[:31])
    worksheet.append(headers)
    for cell in worksheet[1]:
        cell.font = Font(bold=True)
    for row in rows:
        worksheet.append(row)
    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = worksheet.dimensions


def workbook_bytes_from_product_export(products_queryset, title="Products"):
    try:
        from openpyxl import Workbook
    except ImportError as exc:
        raise ValidationError("openpyxl не установлен. Добавьте пакет в окружение перед экспортом XLSX.") from exc

    products = _load_products(products_queryset)
    headers, rows = _build_product_rows(products)
    workbook = Workbook()
    workbook.remove(workbook.active)
    workbook.properties.title = title
    _append_worksheet(workbook, "Products", headers, rows)
    for sheet_title, sheet_headers, sheet_rows in _related_sheets(products):
        _append_worksheet(workbook, sheet_title, sheet_headers, sheet_rows)

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
