from django.shortcuts import get_object_or_404

from shop.models import Characteristic, ProductCharacteristic


def serialize_product_attributes(product_id):
    product_chars = ProductCharacteristic.objects.filter(product_id=product_id).select_related("characteristic")
    return [
        {
            "attribute_id": pc.characteristic.id,
            "name": pc.characteristic.name,
            "unit": pc.characteristic.unit,
            "value": pc.value,
        }
        for pc in product_chars
    ]


def create_product_attribute_value(product, *, attribute_id, value):
    characteristic = get_object_or_404(
        Characteristic,
        id=attribute_id,
        group=product.group,
    )
    return ProductCharacteristic.objects.create(
        product=product,
        characteristic=characteristic,
        value=value,
    )
