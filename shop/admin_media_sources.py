from shop.admin_media_helpers import guess_media_mime_type, iter_json_media_items
from shop.file_utils import infer_file_kind
from shop.models import (
    Brand,
    Group,
    News,
    NewsAttachment,
    Product,
    ProductCertificate,
    ProductGalleryItem,
    ProductMedia,
    Sert,
    Slider,
)


def iter_media_library_source_entries():
    for brand in Brand.objects.exclude(media__isnull=True).exclude(media=""):
        yield {"url": brand.media, "title": brand.name, "usage_label": "Brand image", "source_obj": brand, "kind": "image"}

    for group in Group.objects.exclude(media__isnull=True).exclude(media=""):
        yield {"url": group.media, "title": group.name, "usage_label": "Group image", "source_obj": group, "kind": "image"}

    for slider in Slider.objects.exclude(image__isnull=True).exclude(image=""):
        yield {"url": slider.image, "title": slider.title, "usage_label": "Slider image", "source_obj": slider, "kind": "image"}

    for news in News.objects.exclude(media__isnull=True).exclude(media=""):
        for item in iter_json_media_items(news.media):
            yield {
                "url": item["url"],
                "storage_path": item["storage_path"],
                "title": item["title"] or news.title,
                "usage_label": "News media field",
                "source_obj": news,
                "kind": "image",
            }

    for product in Product.objects.exclude(media__isnull=True).exclude(media=""):
        for item in iter_json_media_items(product.media):
            yield {
                "url": item["url"],
                "storage_path": item["storage_path"],
                "title": item["title"] or product.name,
                "usage_label": "Product media field",
                "source_obj": product,
                "kind": "image",
            }

    for media in ProductMedia.objects.all():
        yield {
            "url": media.url,
            "storage_path": media.storage_path,
            "title": media.alt_text or media.product.name,
            "mime_type": media.mime_type,
            "size_bytes": media.size_bytes,
            "usage_label": "Product media",
            "source_obj": media,
            "kind": media.media_kind,
        }

    for gallery_item in ProductGalleryItem.objects.all():
        yield {
            "url": gallery_item.url,
            "storage_path": gallery_item.storage_path,
            "title": gallery_item.title or gallery_item.product.name,
            "mime_type": gallery_item.mime_type,
            "size_bytes": gallery_item.size_bytes,
            "usage_label": "Product gallery",
            "source_obj": gallery_item,
            "kind": gallery_item.file_kind,
        }

    for certificate in ProductCertificate.objects.all():
        yield {
            "url": certificate.url,
            "storage_path": certificate.storage_path,
            "title": certificate.title or certificate.product.name,
            "mime_type": certificate.mime_type,
            "size_bytes": certificate.size_bytes,
            "usage_label": "Product certificate",
            "source_obj": certificate,
            "kind": "document",
        }

    for attachment in NewsAttachment.objects.all():
        yield {
            "url": attachment.url,
            "storage_path": attachment.storage_path,
            "title": attachment.title or attachment.news.title,
            "mime_type": attachment.mime_type,
            "size_bytes": attachment.size_bytes,
            "usage_label": "News attachment",
            "source_obj": attachment,
            "kind": infer_file_kind(guess_media_mime_type(attachment.url, attachment.mime_type)),
        }

    for sert in Sert.objects.exclude(url=""):
        yield {
            "url": sert.url,
            "storage_path": sert.storage_path,
            "title": sert.title,
            "mime_type": sert.mime_type,
            "size_bytes": sert.size_bytes,
            "usage_label": "Sert file",
            "source_obj": sert,
            "kind": infer_file_kind(guess_media_mime_type(sert.url, sert.mime_type)),
        }
