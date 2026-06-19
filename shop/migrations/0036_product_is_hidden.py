from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0035_randomize_product_skus"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="is_hidden",
            field=models.BooleanField(default=False),
        ),
    ]
