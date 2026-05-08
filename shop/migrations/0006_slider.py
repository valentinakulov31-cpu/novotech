from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0005_alter_productmedia_options"),
    ]

    operations = [
        migrations.CreateModel(
            name="Slider",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.CharField(max_length=1024)),
                ("title", models.CharField(max_length=255)),
                ("text", models.TextField(blank=True, null=True)),
                ("slug", models.CharField(max_length=255, unique=True)),
                ("sort_order", models.IntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "db_table": "sliders",
                "ordering": ["sort_order", "id"],
            },
        ),
    ]
