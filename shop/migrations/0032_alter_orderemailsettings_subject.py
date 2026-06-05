from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0031_seed_rich_email_templates"),
    ]

    operations = [
        migrations.AlterField(
            model_name="orderemailsettings",
            name="subject",
            field=models.CharField(
                default="\u0417\u0430\u043a\u0430\u0437 #{{order_id}} \u043e\u0442 {{name}} {{phone}}",
                max_length=255,
            ),
        ),
    ]
