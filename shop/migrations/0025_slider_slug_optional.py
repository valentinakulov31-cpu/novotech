from django.db import migrations, models


def empty_slider_slugs_to_null(apps, schema_editor):
    Slider = apps.get_model("shop", "Slider")
    Slider.objects.filter(slug="").update(slug=None)


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0024_contactinfo_coordinates"),
    ]

    operations = [
        migrations.AlterField(
            model_name="slider",
            name="slug",
            field=models.CharField(blank=True, max_length=255, null=True, unique=True),
        ),
        migrations.RunPython(empty_slider_slugs_to_null, migrations.RunPython.noop),
    ]
