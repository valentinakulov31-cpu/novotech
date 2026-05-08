from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0007_inquiry"),
    ]

    operations = [
        migrations.AlterField(
            model_name="inquiry",
            name="phone",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name="inquiry",
            name="email",
            field=models.EmailField(blank=True, max_length=255, null=True),
        ),
    ]
