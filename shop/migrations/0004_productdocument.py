from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0003_productmedia_sort_order"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("storage_path", models.CharField(max_length=1024)),
                ("url", models.CharField(max_length=1024)),
                ("mime_type", models.CharField(max_length=255)),
                ("size_bytes", models.IntegerField()),
                ("sort_order", models.IntegerField(default=0)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="documents", to="shop.product")),
            ],
            options={
                "db_table": "product_documents",
                "ordering": ["sort_order", "id"],
            },
        ),
    ]
