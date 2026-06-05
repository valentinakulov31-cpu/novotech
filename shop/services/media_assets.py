from shop.models import ProductCertificate, ProductMedia
from shop.file_utils import save_uploaded_file


def ordered_product_media_queryset(product):
    return ProductMedia.objects.filter(product=product).order_by("-is_primary", "sort_order", "id")


def sync_product_media(product):
    ordered_urls = [media.url for media in ordered_product_media_queryset(product) if media.url]
    product.media = ordered_urls or None
    product.save(update_fields=["media"])


def ensure_single_primary(product):
    primary_media = list(ProductMedia.objects.filter(product=product, is_primary=True).order_by("sort_order", "id"))
    if not primary_media:
        first_media = ProductMedia.objects.filter(product=product).order_by("sort_order", "id").first()
        if first_media:
            first_media.is_primary = True
            first_media.save(update_fields=["is_primary"])
        return

    keeper = primary_media[0]
    ProductMedia.objects.filter(product=product, is_primary=True).exclude(pk=keeper.pk).update(is_primary=False)


def _next_related_sort_order(model_class, **filters):
    last_sort_order = (
        model_class.objects.filter(**filters)
        .order_by("-sort_order")
        .values_list("sort_order", flat=True)
        .first()
    )
    return (last_sort_order + 1) if last_sort_order is not None else 0


def create_product_media_from_upload(product, upload):
    uploaded = save_uploaded_file(upload, f"product_{product.id}")
    media = ProductMedia.objects.create(
        product=product,
        storage_path=uploaded["storage_path"],
        url=uploaded["url"],
        mime_type=uploaded["mime_type"],
        media_kind=uploaded["file_kind"],
        size_bytes=uploaded["size_bytes"],
        sort_order=_next_related_sort_order(ProductMedia, product=product),
        is_primary=not ProductMedia.objects.filter(product=product).exists(),
    )
    ensure_single_primary(product)
    sync_product_media(product)
    return media


def create_product_certificate_from_upload(product, upload, *, title=None, sort_order=None):
    uploaded = save_uploaded_file(upload, f"cert_{product.id}")
    resolved_sort_order = sort_order
    if resolved_sort_order is None or str(resolved_sort_order).strip() == "":
        resolved_sort_order = _next_related_sort_order(ProductCertificate, product=product)

    return ProductCertificate.objects.create(
        product=product,
        title=(title or upload.name).strip(),
        storage_path=uploaded["storage_path"],
        url=uploaded["url"],
        mime_type=uploaded["mime_type"],
        size_bytes=uploaded["size_bytes"],
        sort_order=int(resolved_sort_order),
    )
