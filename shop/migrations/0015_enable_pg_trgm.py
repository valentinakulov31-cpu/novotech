from django.db import migrations


def enable_pg_trgm(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")


def disable_pg_trgm(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("DROP EXTENSION IF EXISTS pg_trgm;")


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0014_product_characteristics_html'),
    ]

    operations = [
        migrations.RunPython(
            enable_pg_trgm,
            disable_pg_trgm,
        ),
    ]
