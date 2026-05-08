from django.db import migrations, models
from django.utils.text import slugify


def populate_characteristic_slugs(apps, schema_editor):
    Characteristic = apps.get_model("shop", "Characteristic")
    for characteristic in Characteristic.objects.all():
        base_slug = slugify(characteristic.name, allow_unicode=True) or f"characteristic-{characteristic.pk}"
        characteristic.slug = base_slug
        characteristic.save(update_fields=["slug"])


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="characteristic",
            name="data_type",
            field=models.CharField(default="text", max_length=50),
        ),
        migrations.AddField(
            model_name="characteristic",
            name="is_filterable",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="characteristic",
            name="is_searchable",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="characteristic",
            name="slug",
            field=models.CharField(default="", max_length=255),
        ),
        migrations.RunPython(populate_characteristic_slugs, migrations.RunPython.noop),
    ]
