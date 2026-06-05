from django.db import transaction

from shop.models import PublicOrder, PublicOrderItem


def create_public_order(validated_data):
    items = validated_data["items"]
    with transaction.atomic():
        order = PublicOrder.objects.create(
            name=validated_data["name"],
            phone=validated_data["phone"],
            email=validated_data.get("email") or None,
            address=validated_data.get("address") or None,
            comment=validated_data.get("comment") or None,
            total_items=sum(item["qty"] for item in items),
        )
        PublicOrderItem.objects.bulk_create(
            [
                PublicOrderItem(
                    order=order,
                    product_id=item["product_id"],
                    qty=item["qty"],
                )
                for item in items
            ]
        )

    order.refresh_from_db()
    return order
