from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import escape, strip_tags

from shop.models import OrderEmailRecipient, OrderEmailSettings, PublicOrder, PUBLISH_STATUS_PUBLISHED


def get_active_order_email_settings():
    return OrderEmailSettings.objects.filter(status=PUBLISH_STATUS_PUBLISHED).order_by('-updated_at', '-id').first()


def get_active_order_email_recipients():
    return list(
        OrderEmailRecipient.objects.filter(is_active=True)
        .exclude(email='')
        .values_list('email', flat=True)
    )


def _order_items_table(order: PublicOrder) -> str:
    item_rows = ''.join(
        (
            "<tr>"
            f"<td>{escape(item.product.sku)}</td>"
            f"<td>{escape(item.product.name)}</td>"
            f"<td>{item.qty}</td>"
            "</tr>"
        )
        for item in order.items.select_related('product').all()
    )
    return (
        "<table border='1' cellpadding='6' cellspacing='0'>"
        "<thead><tr><th>SKU</th><th>Product</th><th>Qty</th></tr></thead>"
        f"<tbody>{item_rows}</tbody>"
        "</table>"
    )


def _order_items_text(order: PublicOrder) -> str:
    return "\n".join(
        f"{item.product.sku} - {item.product.name} x {item.qty}"
        for item in order.items.select_related('product').all()
    )


def build_order_email_context(order: PublicOrder) -> dict:
    return {
        "order_id": order.id,
        "name": order.name or "",
        "phone": order.phone or "",
        "email": order.email or "",
        "address": order.address or "",
        "comment": order.comment or "",
        "total_items": order.total_items,
        "items_table": _order_items_table(order),
        "items_text": _order_items_text(order),
    }


def render_order_template(template: str | None, context: dict, *, escape_values: bool = True) -> str:
    rendered = str(template or "")
    for key, value in context.items():
        replacement = str(value)
        if escape_values and key != "items_table":
            replacement = escape(replacement)
        rendered = rendered.replace("{{" + key + "}}", replacement)
    return rendered


def build_order_email_html(order: PublicOrder, email_settings: OrderEmailSettings | None) -> str:
    context = build_order_email_context(order)
    intro_html = render_order_template(email_settings.intro_html if email_settings else "", context) if email_settings else ""
    body_html = render_order_template(email_settings.body_html if email_settings else "", context) if email_settings else ""
    footer_html = render_order_template(email_settings.footer_html if email_settings else "", context) if email_settings else ""
    if body_html.strip():
        return f"{intro_html}{body_html}{footer_html}"

    customer_bits = [
        f"<li><strong>Name:</strong> {escape(order.name)}</li>",
        f"<li><strong>Phone:</strong> {escape(order.phone)}</li>",
    ]
    if order.email:
        customer_bits.append(f"<li><strong>Email:</strong> {escape(order.email)}</li>")
    if order.address:
        customer_bits.append(f"<li><strong>Address:</strong> {escape(order.address)}</li>")
    if order.comment:
        customer_bits.append(f"<li><strong>Comment:</strong> {escape(order.comment)}</li>")

    return (
        f"{intro_html}"
        f"<h2>New order #{order.id}</h2>"
        "<h3>Customer</h3>"
        f"<ul>{''.join(customer_bits)}</ul>"
        "<h3>Order items</h3>"
        f"{context['items_table']}"
        f"<p><strong>Total items:</strong> {order.total_items}</p>"
        f"{footer_html}"
    )


def send_public_order_notification(order: PublicOrder) -> bool:
    recipients = get_active_order_email_recipients()
    if not recipients:
        return False

    email_settings = get_active_order_email_settings()
    context = build_order_email_context(order)
    subject_template = (
        email_settings.subject
        if email_settings and email_settings.subject
        else f"New website order #{order.id}"
    )
    subject = render_order_template(subject_template, context, escape_values=False)
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
