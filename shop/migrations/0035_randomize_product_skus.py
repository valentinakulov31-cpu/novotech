import random

from django.db import migrations


def randomize_product_skus(apps, schema_editor):
    from shop.model_search_utils import build_search_index

    Product = apps.get_model("shop", "Product")
    ProductCharacteristic = apps.get_model("shop", "ProductCharacteristic")

    rng = random.SystemRandom()
    existing_skus = set(Product.objects.values_list("sku", flat=True))
    assigned_skus = set()

    def generate_unique_numeric_sku():
        while True:
            sku = str(rng.randrange(10**9, 10**10))
            if sku in existing_skus or sku in assigned_skus:
                continue
            assigned_skus.add(sku)
            return sku

    characteristic_rows = (
        ProductCharacteristic.objects.select_related("characteristic")
        .values_list("product_id", "value", "characteristic__name", "characteristic__slug")
    )
    characteristic_map = {}
    for product_id, value, characteristic_name, characteristic_slug in characteristic_rows:
        characteristic_map.setdefault(product_id, []).append((value, characteristic_name, characteristic_slug))

    for product in Product.objects.select_related("brand", "group").order_by("id"):
        product.sku = generate_unique_numeric_sku()
        product.search_index = build_search_index(
            product.sku,
            product.slug,
            product.name,
            product.description,
            product.characteristics_html,
            product.search_tsv,
            product.brand.name if product.brand else "",
            product.brand.slug if product.brand else "",
            product.brand.search_synonyms if product.brand else [],
            product.group.name if product.group else "",
            product.group.slug if product.group else "",
            product.group.search_synonyms if product.group else [],
            characteristic_map.get(product.id, []),
        )
        product.save(update_fields=["sku", "search_index"])


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0034_catalogimportjob"),
    ]

    operations = [
        migrations.RunPython(randomize_product_skus, migrations.RunPython.noop),
    ]
