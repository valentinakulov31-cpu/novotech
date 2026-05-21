from django.db import migrations, models


def seed_inquiry_template(apps, schema_editor):
    OrderEmailSettings = apps.get_model("shop", "OrderEmailSettings")
    if OrderEmailSettings.objects.filter(notification_type="inquiry").exists():
        return
    OrderEmailSettings.objects.create(
        title="Inquiry email settings",
        notification_type="inquiry",
        subject="Заявка #{{inquiry_id}} от {{name}} {{phone}}",
        intro_html="<p>На сайте появилась новая заявка. Ниже будут автоматически подставлены контакты и сообщение клиента.</p>",
        footer_html="<p>Свяжитесь с клиентом как можно скорее и зафиксируйте результат обработки.</p>",
        status="draft",
    )


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0029_rebuild_search_indexes"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="orderemailrecipient",
            options={
                "db_table": "order_email_recipients",
                "ordering": ["email"],
                "verbose_name": "Email recipient",
                "verbose_name_plural": "Email recipients",
            },
        ),
        migrations.AlterModelOptions(
            name="orderemailsettings",
            options={
                "db_table": "order_email_settings",
                "ordering": ["-updated_at", "-id"],
                "verbose_name": "Email template",
                "verbose_name_plural": "Email templates",
            },
        ),
        migrations.AddField(
            model_name="orderemailsettings",
            name="notification_type",
            field=models.CharField(
                choices=[("order", "Order"), ("inquiry", "Inquiry")],
                default="order",
                max_length=20,
            ),
        ),
        migrations.RemoveField(
            model_name="orderemailsettings",
            name="from_email",
        ),
        migrations.RunPython(seed_inquiry_template, migrations.RunPython.noop),
    ]
