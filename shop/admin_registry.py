from shop.admin_catalog_registry import *  # noqa: F401,F403
from shop.admin_content_registry import *  # noqa: F401,F403
from shop.admin_media_registry import *  # noqa: F401,F403
from shop.admin_orders_registry import *  # noqa: F401,F403
from shop.services import catalog_import as catalog_import_service
from shop.services import media_assets as media_assets_service


# Backward-compatible re-exports used by tests and old admin call sites.
ensure_single_primary = media_assets_service.ensure_single_primary
sync_product_media = media_assets_service.sync_product_media
import_products_from_workbook = catalog_import_service.import_products_from_workbook
build_product_export_rows = catalog_import_service.build_product_export_rows
workbook_bytes_from_headers_and_rows = catalog_import_service.workbook_bytes_from_headers_and_rows
