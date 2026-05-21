import re

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import escape, strip_tags

from shop.models import (
    EMAIL_NOTIFICATION_TYPE_INQUIRY,
    EMAIL_NOTIFICATION_TYPE_ORDER,
    Inquiry,
    OrderEmailRecipient,
    OrderEmailSettings,
    PUBLISH_STATUS_PUBLISHED,
    PublicOrder,
)

PLACEHOLDER_RE = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")


def get_active_email_settings(notification_type: str):
    return (
        OrderEmailSettings.objects.filter(
            status=PUBLISH_STATUS_PUBLISHED,
            notification_type=notification_type,
        )
        .order_by("-updated_at", "-id")
        .first()
    )


def get_active_email_recipients():
    return list(
        OrderEmailRecipient.objects.filter(is_active=True)
        .exclude(email="")
        .values_list("email", flat=True)
    )


def _order_items_table(order: PublicOrder) -> str:
    item_rows = "".join(
        (
            "<tr>"
            f"<td style='padding:12px; border-bottom:1px solid #f2ece3;'>{escape(item.product.sku)}</td>"
            f"<td style='padding:12px; border-bottom:1px solid #f2ece3;'>{escape(item.product.name)}</td>"
            f"<td style='padding:12px; border-bottom:1px solid #f2ece3;'>{item.qty}</td>"
            "</tr>"
        )
        for item in order.items.select_related("product").all()
    )
    return (
        "<table style='width:100%; border-collapse:collapse;'>"
        "<thead><tr>"
        "<th style='text-align:left; padding:12px; border-bottom:1px solid #e6ded3;'>SKU</th>"
        "<th style='text-align:left; padding:12px; border-bottom:1px solid #e6ded3;'>Товар</th>"
        "<th style='text-align:left; padding:12px; border-bottom:1px solid #e6ded3;'>Кол-во</th>"
        "</tr></thead>"
        f"<tbody>{item_rows}</tbody>"
        "</table>"
    )


def _order_items_text(order: PublicOrder) -> str:
    return "\n".join(
        f"{item.product.sku} - {item.product.name} x {item.qty}"
        for item in order.items.select_related("product").all()
    )


def build_order_email_context(order: PublicOrder) -> dict:
    return {
        "order_id": order.id,
        "notification_id": order.id,
        "notification_kind": "заказ",
        "name": order.name or "",
        "phone": order.phone or "",
        "email": order.email or "",
        "address": order.address or "",
        "comment": order.comment or "",
        "total_items": order.total_items,
        "items_table": _order_items_table(order),
        "items_text": _order_items_text(order),
    }


def build_inquiry_email_context(inquiry: Inquiry) -> dict:
    return {
        "inquiry_id": inquiry.id,
        "notification_id": inquiry.id,
        "notification_kind": "заявка",
        "name": inquiry.name or "",
        "phone": inquiry.phone or "",
        "email": inquiry.email or "",
        "message": inquiry.message or "",
        "created_at": inquiry.created_at.strftime("%d.%m.%Y %H:%M"),
    }


def _sample_order_context() -> dict:
    return {
        "order_id": 123,
        "name": "Иван Петров",
        "phone": "+7 (999) 000-11-22",
        "email": "ivan@example.com",
        "address": "Красноярск, ул. Весенняя, 7",
        "comment": "Позвонить перед отгрузкой",
        "total_items": 3,
        "items_table": (
            "<table style='width:100%; border-collapse:collapse;'>"
            "<thead><tr>"
            "<th style='text-align:left; padding:12px; border-bottom:1px solid #e6ded3;'>SKU</th>"
            "<th style='text-align:left; padding:12px; border-bottom:1px solid #e6ded3;'>Товар</th>"
            "<th style='text-align:left; padding:12px; border-bottom:1px solid #e6ded3;'>Кол-во</th>"
            "</tr></thead>"
            "<tbody><tr>"
            "<td style='padding:12px; border-bottom:1px solid #f2ece3;'>ER-0001</td>"
            "<td style='padding:12px; border-bottom:1px solid #f2ece3;'>Цилиндры ENERGOROLL RK</td>"
            "<td style='padding:12px; border-bottom:1px solid #f2ece3;'>3</td>"
            "</tr></tbody></table>"
        ),
        "items_text": "ER-0001 - Цилиндры ENERGOROLL RK x 3",
    }


def _sample_inquiry_context() -> dict:
    return {
        "inquiry_id": 77,
        "name": "Марина Алексеева",
        "phone": "+7 (983) 159-16-73",
        "email": "marina@example.com",
        "message": "Нужна консультация по подбору изоляции для промышленного объекта.",
        "created_at": "21.05.2026 15:30",
    }


def render_email_template(template: str | None, context: dict, *, escape_values: bool = True) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in context:
            return match.group(0)
        replacement = str(context[key])
        if escape_values and key != "items_table":
            replacement = escape(replacement)
        return replacement

    return PLACEHOLDER_RE.sub(replace, str(template or ""))


def _build_order_default_body(context: dict) -> str:
    customer_rows = [
        ("Имя", context["name"]),
        ("Телефон", context["phone"]),
    ]
    if context.get("email"):
        customer_rows.append(("Email", context["email"]))
    if context.get("address"):
        customer_rows.append(("Адрес", context["address"]))
    if context.get("comment"):
        customer_rows.append(("Комментарий", context["comment"]))

    customer_html = "".join(
        (
            "<tr>"
            f"<td style='padding:0 0 10px; color:#7d7468; font-size:13px; width:130px;'>{escape(label)}</td>"
            f"<td style='padding:0 0 10px; color:#171717; font-size:15px; font-weight:600;'>{escape(value)}</td>"
            "</tr>"
        )
        for label, value in customer_rows
    )
    return (
        "<table role='presentation' width='100%' cellspacing='0' cellpadding='0' style='margin:0 0 20px;'>"
        "<tr><td style='padding:0 0 20px;'>"
        "<table role='presentation' width='100%' cellspacing='0' cellpadding='0'><tr><td "
        "style='padding:18px 22px; background:#fbf9f4; border:1px solid #eee5d8; border-radius:18px;'>"
        f"<div style='font-size:12px; text-transform:uppercase; letter-spacing:0.08em; color:#8f867b; margin-bottom:8px;'>Заказ #{escape(context['order_id'])}</div>"
        "<div style='font-size:30px; line-height:1.15; font-weight:800; color:#171717; margin-bottom:8px;'>Новый заказ с сайта</div>"
        f"<div style='font-size:16px; line-height:1.65; color:#5f584f;'>Заказ оформил <strong style='color:#171717;'>{escape(context['name'] or 'клиент')}</strong>. "
        f"Внутри {escape(context['total_items'])} позиций. Ниже вся информация для быстрого контакта и обработки.</div>"
        "</td></tr></table>"
        "</td></tr>"
        "<tr><td style='padding:0 0 18px;'>"
        "<table role='presentation' width='100%' cellspacing='0' cellpadding='0'><tr><td "
        "style='padding:18px 22px; background:#ffffff; border:1px solid #eee5d8; border-radius:18px;'>"
        "<div style='font-size:18px; font-weight:700; color:#171717; margin-bottom:14px;'>Данные клиента</div>"
        f"<table role='presentation' width='100%' cellspacing='0' cellpadding='0'>{customer_html}</table>"
        "</td></tr></table>"
        "</td></tr>"
        "<tr><td>"
        "<table role='presentation' width='100%' cellspacing='0' cellpadding='0'><tr><td "
        "style='padding:18px 22px; background:#ffffff; border:1px solid #eee5d8; border-radius:18px;'>"
        "<div style='font-size:18px; font-weight:700; color:#171717; margin-bottom:14px;'>Состав заказа</div>"
        f"{context['items_table']}"
        f"<div style='margin-top:16px; display:inline-block; padding:10px 14px; background:#ffd400; color:#171717; font-size:14px; font-weight:800; border-radius:999px;'>Всего позиций: {escape(context['total_items'])}</div>"
        "</td></tr></table>"
        "</td></tr>"
        "</table>"
    )


def _build_inquiry_default_body(context: dict) -> str:
    contact_rows = [
        ("Имя", context["name"]),
        ("Телефон", context["phone"] or "Не указан"),
        ("Email", context["email"] or "Не указан"),
        ("Дата", context["created_at"]),
    ]
    contact_html = "".join(
        (
            "<tr>"
            f"<td style='padding:0 0 10px; color:#7d7468; font-size:13px; width:130px;'>{escape(label)}</td>"
            f"<td style='padding:0 0 10px; color:#171717; font-size:15px; font-weight:600;'>{escape(value)}</td>"
            "</tr>"
        )
        for label, value in contact_rows
    )
    message_value = context.get("message") or "Клиент не оставил текст сообщения."
    return (
        "<table role='presentation' width='100%' cellspacing='0' cellpadding='0' style='margin:0 0 20px;'>"
        "<tr><td style='padding:0 0 20px;'>"
        "<table role='presentation' width='100%' cellspacing='0' cellpadding='0'><tr><td "
        "style='padding:18px 22px; background:#fbf9f4; border:1px solid #eee5d8; border-radius:18px;'>"
        f"<div style='font-size:12px; text-transform:uppercase; letter-spacing:0.08em; color:#8f867b; margin-bottom:8px;'>Заявка #{escape(context['inquiry_id'])}</div>"
        "<div style='font-size:30px; line-height:1.15; font-weight:800; color:#171717; margin-bottom:8px;'>Новая заявка с сайта</div>"
        f"<div style='font-size:16px; line-height:1.65; color:#5f584f;'>Заявку оставил <strong style='color:#171717;'>{escape(context['name'] or 'клиент')}</strong>. "
        "Ниже контакты и текст обращения, чтобы менеджер сразу понял контекст.</div>"
        "</td></tr></table>"
        "</td></tr>"
        "<tr><td style='padding:0 0 18px;'>"
        "<table role='presentation' width='100%' cellspacing='0' cellpadding='0'><tr><td "
        "style='padding:18px 22px; background:#ffffff; border:1px solid #eee5d8; border-radius:18px;'>"
        "<div style='font-size:18px; font-weight:700; color:#171717; margin-bottom:14px;'>Контактные данные</div>"
        f"<table role='presentation' width='100%' cellspacing='0' cellpadding='0'>{contact_html}</table>"
        "</td></tr></table>"
        "</td></tr>"
        "<tr><td>"
        "<table role='presentation' width='100%' cellspacing='0' cellpadding='0'><tr><td "
        "style='padding:18px 22px; background:#ffffff; border:1px solid #eee5d8; border-radius:18px;'>"
        "<div style='font-size:18px; font-weight:700; color:#171717; margin-bottom:14px;'>Сообщение клиента</div>"
        f"<div style='padding:18px; background:#f5f1ea; border-radius:14px; font-size:15px; line-height:1.8; color:#2e2a25; white-space:pre-line;'>{escape(message_value)}</div>"
        "</td></tr></table>"
        "</td></tr>"
        "</table>"
    )


def _wrap_email_shell(subject: str, notification_type: str, main_html: str, footer_html: str) -> str:
    label = "Уведомление по заказу" if notification_type == EMAIL_NOTIFICATION_TYPE_ORDER else "Уведомление по заявке"
    return (
        "<!DOCTYPE html>"
        "<html><body style='margin:0; padding:0; background:#e8e2da; font-family:Arial, Helvetica, sans-serif; color:#171717;'>"
        "<table role='presentation' width='100%' cellspacing='0' cellpadding='0' style='background:#e8e2da; padding:32px 16px;'>"
        "<tr><td align='center'>"
        "<table role='presentation' width='100%' cellspacing='0' cellpadding='0' style='max-width:760px;'>"
        "<tr><td style='padding:0 0 16px;'>"
        "<table role='presentation' width='100%' cellspacing='0' cellpadding='0'><tr>"
        "<td style='font-size:36px; font-weight:900; color:#171717; letter-spacing:0.01em;'>НОВАТЕХ</td>"
        f"<td align='right'><span style='display:inline-block; padding:10px 16px; background:#ffd400; border-radius:999px; font-size:12px; font-weight:700; text-transform:uppercase; color:#171717;'>{label}</span></td>"
        "</tr></table>"
        "</td></tr>"
        "<tr><td style='background:#ffffff; border-radius:28px; padding:36px 32px; box-shadow:0 18px 40px rgba(23,23,23,0.08);'>"
        f"<div style='font-size:38px; line-height:1.1; font-weight:800; color:#171717; margin:0 0 10px;'>{escape(subject)}</div>"
        "<div style='width:120px; height:4px; background:#ffd400; border-radius:999px; margin:0 0 24px;'></div>"
        f"{main_html}"
        f"<div style='margin-top:28px; padding-top:18px; border-top:1px solid #eee5d8; font-size:13px; line-height:1.7; color:#6c655d;'>{footer_html}</div>"
        "</td></tr>"
        "<tr><td style='padding:18px 8px 0; font-size:12px; line-height:1.6; color:#7d7468; text-align:center;'>"
        "Письмо отправлено автоматически с сайта НОВАТЕХ. Жёлтые акценты и светлая композиция повторяют визуальный стиль сайта."
        "</td></tr>"
        "</table>"
        "</td></tr>"
        "</table>"
        "</body></html>"
    )


def build_notification_email_html(notification_type: str, context: dict, email_settings: OrderEmailSettings | None) -> str:
    if email_settings:
        intro_html = render_email_template(email_settings.intro_html or "", context)
        body_html = render_email_template(email_settings.body_html or "", context)
        footer_html = render_email_template(email_settings.footer_html or "", context)
        subject_template = email_settings.subject
    else:
        intro_html = ""
        body_html = (
            _build_order_default_body(context)
            if notification_type == EMAIL_NOTIFICATION_TYPE_ORDER
            else _build_inquiry_default_body(context)
        )
        footer_html = ""
        subject_template = (
            "Заказ #{{order_id}} от {{name}} {{phone}}"
            if notification_type == EMAIL_NOTIFICATION_TYPE_ORDER
            else "Заявка #{{inquiry_id}} от {{name}} {{phone}}"
        )

    subject = render_email_template(subject_template, context, escape_values=False)
    return _wrap_email_shell(subject, notification_type, f"{intro_html}{body_html}", footer_html)


def build_notification_preview_html(notification_type: str, email_settings: OrderEmailSettings | None) -> str:
    context = _sample_order_context() if notification_type == EMAIL_NOTIFICATION_TYPE_ORDER else _sample_inquiry_context()
    return build_notification_email_html(notification_type, context, email_settings)


def _send_notification(notification_type: str, context: dict) -> bool:
    recipients = get_active_email_recipients()
    if not recipients:
        return False

    email_settings = get_active_email_settings(notification_type)
    subject_template = (
        email_settings.subject
        if email_settings and email_settings.subject
        else (
            "Заказ #{{order_id}} от {{name}} {{phone}}"
            if notification_type == EMAIL_NOTIFICATION_TYPE_ORDER
            else "Заявка #{{inquiry_id}} от {{name}} {{phone}}"
        )
    )
    subject = render_email_template(subject_template, context, escape_values=False)
    html_body = build_notification_email_html(notification_type, context, email_settings)
    text_body = strip_tags(html_body)

    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
    )
    message.attach_alternative(html_body, "text/html")
    message.send(fail_silently=False)
    return True


def send_public_order_notification(order: PublicOrder) -> bool:
    return _send_notification(EMAIL_NOTIFICATION_TYPE_ORDER, build_order_email_context(order))


def send_inquiry_notification(inquiry: Inquiry) -> bool:
    return _send_notification(EMAIL_NOTIFICATION_TYPE_INQUIRY, build_inquiry_email_context(inquiry))
