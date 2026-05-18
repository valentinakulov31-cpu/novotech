from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0026_admin_cleanup_synonyms_email_templates"),
    ]

    operations = [
        migrations.AddField(
            model_name="contactinfo",
            name="gis_link",
            field=models.URLField(blank=True, max_length=1024, null=True),
        ),
        migrations.AddField(
            model_name="contactinfo",
            name="yandex_link",
            field=models.URLField(blank=True, max_length=1024, null=True),
        ),
    ]
