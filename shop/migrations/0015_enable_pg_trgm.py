from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0014_product_characteristics_html'),
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS pg_trgm;",
            reverse_sql="DROP EXTENSION IF EXISTS pg_trgm;",
        ),
    ]
