from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0002_characteristic_contract_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="productmedia",
            name="sort_order",
            field=models.IntegerField(default=0),
        ),
    ]
