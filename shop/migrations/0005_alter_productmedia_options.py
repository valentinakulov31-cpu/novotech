from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0004_productdocument"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="productmedia",
            options={"ordering": ["-is_primary", "sort_order", "id"]},
        ),
    ]
