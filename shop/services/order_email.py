from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags

from shop.models import OrderEmailRecipient, OrderEmailSettings, PublicOrder, PUBLISH_STATUS_PUBLISHED


def get_active_order_email_settings():
    return OrderEmailSettings.objects.filter(status=PUBLISH_STATUS_PUBLISHED).order_by('-updated_at', '-id').first()


def get_active_order_email_recipients():
    return list(
        OrderEmailRecipient.objects.filter(is_active=True)
        .exclude(email='')
        .values_list('email', flat=True)
    )


def build_order_email_html(order: PublicOrder, email_settings: OrderEmailSettings | None) -> str:
    intro_html = (email_settings.intro_html if email_settings else '') or ''
    footer_html = (email_settings.footer_html if email_settings else '') or ''
    customer_bits = [
        f"<li><strong>Имя:</strong> {order.name}</li>",
        f"<li><strong>Телефон:</strong> {order.phone}</li>",
    ]
    if order.email:
        customer_bits.append(f"<li><strong>Email:</strong> {order.email}</li>")
    if order.address:
        customer_bits.append(f"<li><strong>Адрес:</strong> {order.address}</li>")
    if order.comment:
        customer_bits.append(f"<li><strong>Комментарий:</strong> {order.comment}</li>")

    item_rows = ''.join(
        (
            "<tr>"
            f"<td>{item.product.sku}</td>"
            f"<td>{item.product.name}</td>"
            f"<td>{item.qty}</td>"
            "</tr>"
        )
        for item in order.items.select_related('product').all()
    )

    return (
        f"{intro_html}"
        f"<h2>Новый заказ #{order.id}</h2>"
        "<h3>Клиент</h3>"
        f"<ul>{''.join(customer_bits)}</ul>"
        "<h3>Состав заказа</h3>"
        "<table border='1' cellpadding='6' cellspacing='0'>"
        "<thead><tr><th>SKU</th><th>Товар</th><th>Количество</th></tr></thead>"
        f"<tbody>{item_rows}</tbody>"
        "</table>"
        f"<p><strong>Всего позиций:</strong> {order.total_items}</p>"
        f"{footer_html}"
    )


def send_public_order_notification(order: PublicOrder) -> bool:
    recipients = get_active_order_email_recipients()
    if not recipients:
        return False

    email_settings = get_active_order_email_settings()
    subject = (
        email_settings.subject
        if email_settings and email_settings.subject
        else f"Новый заказ с сайта #{order.id}"
    )
    from_email = (
        email_settings.from_email
        if email_settings and email_settings.from_email
        else settings.DEFAULT_FROM_EMAIL
    )
    html_body = build_order_email_html(order, email_settings)
    text_body = strip_tags(html_body)

    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=from_email,
        to=recipients,
    )
    message.attach_alternative(html_body, 'text/html')
    message.send(fail_silently=False)
    return True
