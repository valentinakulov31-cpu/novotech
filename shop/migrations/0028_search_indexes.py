from django.db import migrations, models


def populate_search_indexes(apps, schema_editor):
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


def create_pg_search_indexes(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    schema_editor.execute(
        "CREATE INDEX IF NOT EXISTS shop_brand_search_index_trgm "
        "ON brands USING gin (search_index gin_trgm_ops);"
    )
    schema_editor.execute(
        "CREATE INDEX IF NOT EXISTS shop_group_search_index_trgm "
        "ON groups USING gin (search_index gin_trgm_ops);"
    )
    schema_editor.execute(
        "CREATE INDEX IF NOT EXISTS shop_product_search_index_trgm "
        "ON products USING gin (search_index gin_trgm_ops);"
    )
    schema_editor.execute(
        "CREATE INDEX IF NOT EXISTS shop_characteristic_search_index_trgm "
        "ON characteristics USING gin (search_index gin_trgm_ops);"
    )


def drop_pg_search_indexes(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("DROP INDEX IF EXISTS shop_brand_search_index_trgm;")
    schema_editor.execute("DROP INDEX IF EXISTS shop_group_search_index_trgm;")
    schema_editor.execute("DROP INDEX IF EXISTS shop_product_search_index_trgm;")
    schema_editor.execute("DROP INDEX IF EXISTS shop_characteristic_search_index_trgm;")


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0027_contactinfo_map_links"),
    ]

    operations = [
        migrations.AddField(
            model_name="brand",
            name="search_index",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="characteristic",
            name="search_index",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="group",
            name="search_index",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="product",
            name="search_index",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.RunPython(populate_search_indexes, migrations.RunPython.noop),
        migrations.RunPython(
            create_pg_search_indexes,
            drop_pg_search_indexes,
        ),
    ]
