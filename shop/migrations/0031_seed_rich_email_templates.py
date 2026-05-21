from django.db import migrations


ORDER_SUBJECT = "Заказ #{{order_id}} от {{name}} {{phone}}"
ORDER_INTRO = (
    "<p>На сайте появился новый заказ. Ниже автоматически подставятся "
    "контакты клиента, комментарий и состав заказа.</p>"
)
ORDER_BODY = """
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:0 0 20px;">
  <tr><td style="padding:0 0 20px;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td style="padding:18px 22px; background:#fbf9f4; border:1px solid #eee5d8; border-radius:18px;">
      <div style="font-size:12px; text-transform:uppercase; letter-spacing:0.08em; color:#8f867b; margin-bottom:8px;">Заказ #{{order_id}}</div>
      <div style="font-size:30px; line-height:1.15; font-weight:800; color:#171717; margin-bottom:8px;">Новый заказ с сайта</div>
      <div style="font-size:16px; line-height:1.65; color:#5f584f;">Заказ оформил <strong style="color:#171717;">{{name}}</strong>. Внутри {{total_items}} позиций. Ниже вся информация для быстрого контакта и обработки.</div>
    </td></tr></table>
  </td></tr>
  <tr><td style="padding:0 0 18px;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td style="padding:18px 22px; background:#ffffff; border:1px solid #eee5d8; border-radius:18px;">
      <div style="font-size:18px; font-weight:700; color:#171717; margin-bottom:14px;">Данные клиента</div>
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
        <tr><td style="padding:0 0 10px; color:#7d7468; font-size:13px; width:130px;">Имя</td><td style="padding:0 0 10px; color:#171717; font-size:15px; font-weight:600;">{{name}}</td></tr>
        <tr><td style="padding:0 0 10px; color:#7d7468; font-size:13px; width:130px;">Телефон</td><td style="padding:0 0 10px; color:#171717; font-size:15px; font-weight:600;">{{phone}}</td></tr>
        <tr><td style="padding:0 0 10px; color:#7d7468; font-size:13px; width:130px;">Email</td><td style="padding:0 0 10px; color:#171717; font-size:15px; font-weight:600;">{{email}}</td></tr>
        <tr><td style="padding:0 0 10px; color:#7d7468; font-size:13px; width:130px;">Адрес</td><td style="padding:0 0 10px; color:#171717; font-size:15px; font-weight:600;">{{address}}</td></tr>
        <tr><td style="padding:0; color:#7d7468; font-size:13px; width:130px;">Комментарий</td><td style="padding:0; color:#171717; font-size:15px; font-weight:600;">{{comment}}</td></tr>
      </table>
    </td></tr></table>
  </td></tr>
  <tr><td>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td style="padding:18px 22px; background:#ffffff; border:1px solid #eee5d8; border-radius:18px;">
      <div style="font-size:18px; font-weight:700; color:#171717; margin-bottom:14px;">Состав заказа</div>
      {{items_table}}
      <div style="margin-top:16px; display:inline-block; padding:10px 14px; background:#ffd400; color:#171717; font-size:14px; font-weight:800; border-radius:999px;">Всего позиций: {{total_items}}</div>
    </td></tr></table>
  </td></tr>
</table>
""".strip()
ORDER_FOOTER = (
    "<p>Проверьте состав, свяжитесь с клиентом и зафиксируйте следующий шаг "
    "по обработке заказа.</p>"
)

INQUIRY_SUBJECT = "Заявка #{{inquiry_id}} от {{name}} {{phone}}"
INQUIRY_INTRO = (
    "<p>На сайте появилась новая заявка. Ниже автоматически подставятся "
    "контакты клиента и текст обращения.</p>"
)
INQUIRY_BODY = """
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:0 0 20px;">
  <tr><td style="padding:0 0 20px;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td style="padding:18px 22px; background:#fbf9f4; border:1px solid #eee5d8; border-radius:18px;">
      <div style="font-size:12px; text-transform:uppercase; letter-spacing:0.08em; color:#8f867b; margin-bottom:8px;">Заявка #{{inquiry_id}}</div>
      <div style="font-size:30px; line-height:1.15; font-weight:800; color:#171717; margin-bottom:8px;">Новая заявка с сайта</div>
      <div style="font-size:16px; line-height:1.65; color:#5f584f;">Заявку оставил <strong style="color:#171717;">{{name}}</strong>. Ниже контакты и текст обращения, чтобы менеджер сразу понял контекст.</div>
    </td></tr></table>
  </td></tr>
  <tr><td style="padding:0 0 18px;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td style="padding:18px 22px; background:#ffffff; border:1px solid #eee5d8; border-radius:18px;">
      <div style="font-size:18px; font-weight:700; color:#171717; margin-bottom:14px;">Контактные данные</div>
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
        <tr><td style="padding:0 0 10px; color:#7d7468; font-size:13px; width:130px;">Имя</td><td style="padding:0 0 10px; color:#171717; font-size:15px; font-weight:600;">{{name}}</td></tr>
        <tr><td style="padding:0 0 10px; color:#7d7468; font-size:13px; width:130px;">Телефон</td><td style="padding:0 0 10px; color:#171717; font-size:15px; font-weight:600;">{{phone}}</td></tr>
        <tr><td style="padding:0 0 10px; color:#7d7468; font-size:13px; width:130px;">Email</td><td style="padding:0 0 10px; color:#171717; font-size:15px; font-weight:600;">{{email}}</td></tr>
        <tr><td style="padding:0; color:#7d7468; font-size:13px; width:130px;">Дата</td><td style="padding:0; color:#171717; font-size:15px; font-weight:600;">{{created_at}}</td></tr>
      </table>
    </td></tr></table>
  </td></tr>
  <tr><td>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td style="padding:18px 22px; background:#ffffff; border:1px solid #eee5d8; border-radius:18px;">
      <div style="font-size:18px; font-weight:700; color:#171717; margin-bottom:14px;">Сообщение клиента</div>
      <div style="padding:18px; background:#f5f1ea; border-radius:14px; font-size:15px; line-height:1.8; color:#2e2a25; white-space:pre-line;">{{message}}</div>
    </td></tr></table>
  </td></tr>
</table>
""".strip()
INQUIRY_FOOTER = (
    "<p>Свяжитесь с клиентом как можно скорее и зафиксируйте результат "
    "обработки заявки.</p>"
)


def _upsert_template(OrderEmailSettings, notification_type, title, subject, intro_html, body_html, footer_html):
    template = (
        OrderEmailSettings.objects.filter(notification_type=notification_type)
        .order_by("-updated_at", "-id")
        .first()
    )
    if template is None:
        template = OrderEmailSettings(notification_type=notification_type)

    template.title = title
    template.subject = subject
    template.intro_html = intro_html
    template.body_html = body_html
    template.footer_html = footer_html
    template.status = "published"
    template.save()

    (
        OrderEmailSettings.objects.filter(notification_type=notification_type)
        .exclude(pk=template.pk)
        .update(status="draft")
    )


def seed_rich_email_templates(apps, schema_editor):
    OrderEmailSettings = apps.get_model("shop", "OrderEmailSettings")
    _upsert_template(
        OrderEmailSettings,
        "order",
        "Order email settings",
        ORDER_SUBJECT,
        ORDER_INTRO,
        ORDER_BODY,
        ORDER_FOOTER,
    )
    _upsert_template(
        OrderEmailSettings,
        "inquiry",
        "Inquiry email settings",
        INQUIRY_SUBJECT,
        INQUIRY_INTRO,
        INQUIRY_BODY,
        INQUIRY_FOOTER,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0030_email_templates_for_inquiries"),
    ]

    operations = [
        migrations.RunPython(seed_rich_email_templates, migrations.RunPython.noop),
    ]
