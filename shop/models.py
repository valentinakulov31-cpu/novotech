from shop.model_constants import (
    CHARACTERISTIC_TYPE_BOOLEAN,
    CHARACTERISTIC_TYPE_CHOICES,
    CHARACTERISTIC_TYPE_NUMBER,
    CHARACTERISTIC_TYPE_TEXT,
    EMAIL_NOTIFICATION_TYPE_CHOICES,
    EMAIL_NOTIFICATION_TYPE_INQUIRY,
    EMAIL_NOTIFICATION_TYPE_ORDER,
    PUBLISH_STATUS_CHOICES,
    PUBLISH_STATUS_DRAFT,
    PUBLISH_STATUS_PUBLISHED,
)
from shop.model_utils import (
    assign_sort_order as _assign_sort_order,
    build_search_index as _build_search_index,
    include_update_fields as _include_update_fields,
    normalize_search_token as _normalize_search_token,
    normalize_synonyms as _normalize_synonyms,
    next_sort_order as _next_sort_order,
    search_text_parts as _search_text_parts,
    transliterate_slug as _transliterate_slug,
    unique_product_slug as _unique_product_slug,
)
from shop.models_catalog import (
    Brand,
    Characteristic,
    City,
    Group,
    MediaLibrary,
    Product,
    ProductCertificate,
    ProductCharacteristic,
    ProductGalleryItem,
    ProductMedia,
)
from shop.models_content import Agent, ContactInfo, HtmlContent, Inquiry, News, NewsAttachment, Sert, Slider
from shop.models_orders import OrderEmailRecipient, OrderEmailSettings, PublicOrder, PublicOrderItem


def normalize_search_token(value: str) -> str:
    return _normalize_search_token(value)


def transliterate_slug(value: str) -> str:
    return _transliterate_slug(value)


def unique_product_slug(instance, base_value: str) -> str:
    return _unique_product_slug(instance, base_value)


def next_sort_order(model_class, filters=None) -> int:
    return _next_sort_order(model_class, filters=filters)


def assign_sort_order(instance, filters=None):
    return _assign_sort_order(instance, filters=filters)


def include_update_fields(kwargs, *field_names):
    return _include_update_fields(kwargs, *field_names)


def normalize_synonyms(value):
    return _normalize_synonyms(value)


def search_text_parts(*values):
    return _search_text_parts(*values)


def build_search_index(*values):
    return _build_search_index(*values)
