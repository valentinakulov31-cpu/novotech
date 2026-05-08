from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("shop", "0017_alter_contactinfo_title_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="MediaLibrary",
            fields=[],
            options={
                "verbose_name": "Media library",
                "verbose_name_plural": "Media library",
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("shop.productmedia",),
        ),
    ]
