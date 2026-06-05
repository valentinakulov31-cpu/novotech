from pathlib import Path

from django.db import transaction
from django.db.models import Q

from shop.admin_media_helpers import (
    media_item_matches,
    resolve_media_storage_path,
    strip_asset_from_json_media,
)
from shop.models import (
    Brand,
    ContactInfo,
    Group,
    MediaLibrary,
    News,
    NewsAttachment,
    Product,
    ProductCertificate,
    ProductGalleryItem,
    ProductMedia,
    Sert,
    Slider,
)


def build_media_match_q(asset_url: str | None, asset_storage_path: str | None):
    match_q = Q()
    if asset_url:
        match_q |= Q(url=asset_url)
    if asset_storage_path:
        normalized_path = resolve_media_storage_path(storage_path=asset_storage_path)
        match_q |= Q(storage_path=asset_storage_path)
        if normalized_path and normalized_path != asset_storage_path:
            match_q |= Q(storage_path=normalized_path)
    return match_q


def delete_media_asset(asset_url: str | None, asset_storage_path: str | None) -> dict:
    normalized_storage_path = resolve_media_storage_path(url=asset_url, storage_path=asset_storage_path)
    result = {
        "deleted_rows": {
            "product_media": 0,
            "product_gallery": 0,
            "product_certificates": 0,
            "news_attachments": 0,
            "serts": 0,
            "library_refs": 0,
        },
        "cleared_fields": {
            "brands": 0,
            "groups": 0,
            "sliders": 0,
            "contacts": 0,
        },
        "updated_products": 0,
        "updated_news": 0,
        "affected_product_count": 0,
        "file_deleted": False,
    }

    with transaction.atomic():
        match_q = build_media_match_q(asset_url, normalized_storage_path or asset_storage_path)

        product_media_qs = ProductMedia.objects.filter(match_q)
        affected_product_ids = set(product_media_qs.values_list("product_id", flat=True))
        result["deleted_rows"]["product_media"] = product_media_qs.count()
        product_media_qs.delete()

        product_gallery_qs = ProductGalleryItem.objects.filter(match_q)
        affected_product_ids.update(product_gallery_qs.values_list("product_id", flat=True))
        result["deleted_rows"]["product_gallery"] = product_gallery_qs.count()
        product_gallery_qs.delete()

        product_cert_qs = ProductCertificate.objects.filter(match_q)
        affected_product_ids.update(product_cert_qs.values_list("product_id", flat=True))
        result["deleted_rows"]["product_certificates"] = product_cert_qs.count()
        product_cert_qs.delete()

        news_attachment_qs = NewsAttachment.objects.filter(match_q)
        result["deleted_rows"]["news_attachments"] = news_attachment_qs.count()
        news_attachment_qs.delete()

        sert_qs = Sert.objects.filter(match_q)
        result["deleted_rows"]["serts"] = sert_qs.count()
        sert_qs.delete()

        for brand in Brand.objects.filter(media=asset_url):
            brand.media = None
            brand.save(update_fields=["media"])
            result["cleared_fields"]["brands"] += 1

        for group in Group.objects.filter(media=asset_url):
            group.media = None
            group.save(update_fields=["media"])
            result["cleared_fields"]["groups"] += 1

        for slider in Slider.objects.filter(image=asset_url):
            slider.image = None
            slider.save(update_fields=["image"])
            result["cleared_fields"]["sliders"] += 1

        for news in News.objects.all():
            current_media = news.media
            new_media = None
            if media_item_matches(current_media, asset_url, normalized_storage_path or asset_storage_path):
                new_media = None
            elif isinstance(current_media, list):
                stripped = strip_asset_from_json_media(current_media, asset_url, normalized_storage_path or asset_storage_path)
                new_media = stripped or None
            else:
                continue
            if new_media != current_media:
                news.media = new_media
                news.save(update_fields=["media"])
                result["updated_news"] += 1

        for product in Product.objects.all():
            current_media = product.media
            if media_item_matches(current_media, asset_url, normalized_storage_path or asset_storage_path):
                updated_media = None
            else:
                updated_media = strip_asset_from_json_media(current_media, asset_url, normalized_storage_path or asset_storage_path)
            if updated_media != current_media:
                product.media = updated_media
                product.save(update_fields=["media"])
                result["updated_products"] += 1
                affected_product_ids.add(product.pk)

        for contact in ContactInfo.objects.filter(Q(yandex_link=asset_url) | Q(gis_link=asset_url)):
            if contact.yandex_link == asset_url:
                contact.yandex_link = ""
            if contact.gis_link == asset_url:
                contact.gis_link = ""
            contact.save(update_fields=["yandex_link", "gis_link"])
            result["cleared_fields"]["contacts"] += 1

        library_qs = MediaLibrary.objects.filter(match_q)
        result["deleted_rows"]["library_refs"] = library_qs.count()
        library_qs.delete()

        if normalized_storage_path:
            file_path = Path(normalized_storage_path)
            if file_path.exists() and file_path.is_file():
                file_path.unlink()
                result["file_deleted"] = True

    result["affected_product_count"] = len(affected_product_ids)
    return result
