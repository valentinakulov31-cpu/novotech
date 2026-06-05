from shop.admin_html_support import render_multiline_text, sanitize_catalog_tables
from shop.admin_media_support import (
    build_admin_change_url,
    build_media_asset_key,
    collect_media_library_assets,
    delete_media_asset,
    extract_media_url,
    guess_media_mime_type,
    is_local_media_url,
    iter_json_media_items,
    mark_generated_file_fields_optional,
    media_item_matches,
    resolve_media_storage_path,
    save_admin_upload,
    strip_asset_from_json_media,
    validate_new_file_upload,
)


SEO_FIELD_NAMES = (
    "seo_title",
    "seo_h1",
    "seo_description",
    "seo_keywords",
    "seo_canonical_url",
    "seo_robots",
)
SEO_AUTO_HELP_TEXT = "Leave empty to let the API generate this SEO value automatically."
SEO_GROUP_PLACEHOLDER_HELP_TEXT = (
    "Supports placeholders: {name}, {slug}, {parent}, {city}, {city_slug}, {city_prep}."
)
