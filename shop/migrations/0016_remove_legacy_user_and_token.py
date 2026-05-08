from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("shop", "0015_enable_pg_trgm"),
    ]

    operations = [
        migrations.DeleteModel(
            name="UserToken",
        ),
        migrations.DeleteModel(
            name="User",
        ),
    ]
