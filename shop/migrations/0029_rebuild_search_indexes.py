from django.db import migrations


def rebuild_search_indexes(apps, schema_editor):
    from shop.models import build_search_index

    Brand = apps.get_model("shop", "Brand")
    Group = apps.get_model("shop", "Group")
    Product = apps.get_model("shop", "Product")
    Characteristic = apps.get_model("shop", "Characteristic")

    for brand in Brand.objects.all():
        brand.search_index = build_search_index(brand.name, brand.slug, brand.search_synonyms)
        brand.save(update_fields=["search_index"])

    for group in Group.objects.all():
        group.search_index = build_search_index(group.name, group.slug, group.description, group.search_synonyms)
        group.save(update_fields=["search_index"])

    for characteristic in Characteristic.objects.select_related("group"):
        characteristic.search_index = build_search_index(
            characteristic.name,
            characteristic.slug,
            characteristic.unit,
            characteristic.group.name if characteristic.group else "",
            characteristic.group.slug if characteristic.group else "",
        )
        characteristic.save(update_fields=["search_index"])

    for product in Product.objects.select_related("brand", "group").prefetch_related("characteristics__characteristic"):
        characteristic_values = [
            (row.value, row.characteristic.name, row.characteristic.slug)
            for row in product.characteristics.all()
        ]
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
            characteristic_values,
        )
        product.save(update_fields=["search_index"])


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0028_search_indexes"),
    ]

    operations = [
        migrations.RunPython(rebuild_search_indexes, migrations.RunPython.noop),
    ]
