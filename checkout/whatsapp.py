import logging
import re

import requests
from django.conf import settings
from django.utils import timezone

from .models import WhatsAppMessage


logger = logging.getLogger(__name__)


def clean_phone_number(phone_number):
    """Return a phone number containing digits only."""

    if not phone_number:
        return ""

    return re.sub(r"\D", "", str(phone_number))


def get_delivery_date(order):
    """Return a readable delivery date."""

    if not order.delivery_date:
        return "Not selected"

    return order.delivery_date.strftime("%d %B %Y")


def get_delivery_time(order):
    """Return the selected delivery time range."""

    if not order.delivery_time:
        return "Not selected"

    return order.get_delivery_time_display()


def build_order_items(order):
    """Build product and greeting-card details."""

    item_lines = []

    line_items = order.lineitems.select_related("product").all()

    for item in line_items:
        line = (
            f"• {item.product.name}\n"
            f"  Quantity: {item.quantity}\n"
            f"  Total: ${item.lineitem_total:.2f}"
        )

        if item.extra_flowers:
            line += (
                f"\n  Extra flowers: "
                f"{item.extra_flowers}"
            )

        if item.greeting_message:
            line += (
                f"\n  Greeting card: "
                f"{item.greeting_message}"
            )
        else:
            line += "\n  Greeting card: No message provided"

        item_lines.append(line)

    if not item_lines:
        return "No products found."

    return "\n\n".join(item_lines)


def build_paid_order_message(order):
    """Create a WhatsApp message with complete order details."""

    customer_phone = clean_phone_number(
        order.phone_number
    )
    items = build_order_items(order)

    delivery_address_parts = [
        order.street_address1,
        order.street_address2,
        order.town_or_city,
        order.county,
        order.postcode,
        str(order.country),
    ]

    delivery_address = ", ".join(
        str(part).strip()
        for part in delivery_address_parts
        if part
    )

    return (
        "🌸 NEW PAID ORDER 🌸\n\n"
        f"Order number: {order.order_number}\n"
        "Payment status: Paid\n"
        f"Customer: {order.full_name}\n"
        f"Email: {order.email}\n"
        f"Phone: {customer_phone}\n\n"
        "DELIVERY INFORMATION\n"
        f"Date: {get_delivery_date(order)}\n"
        f"Time: {get_delivery_time(order)}\n"
        f"Address: {delivery_address}\n\n"
        "ORDER DETAILS\n"
        f"{items}\n\n"
        "PAYMENT\n"
        f"Order total: ${order.order_total:.2f}\n"
        f"Delivery: ${order.delivery_cost:.2f}\n"
        f"Grand total: ${order.grand_total:.2f}"
    )


def send_paid_order_whatsapp(order):
    """Send and store a WhatsApp notification for a paid order."""

    if not order.is_paid:
        logger.warning(
            "WhatsApp message blocked for unpaid order %s",
            order.order_number,
        )
        return None

    recipient = clean_phone_number(
        settings.WHATSAPP_ORDER_RECIPIENT
    )

    message_body = build_paid_order_message(order)

    message_record = WhatsAppMessage.objects.create(
        order=order,
        recipient=recipient,
        message_body=message_body,
        status=WhatsAppMessage.STATUS_PENDING,
    )

    if not recipient:
        message_record.status = WhatsAppMessage.STATUS_FAILED
        message_record.error_message = (
            "WHATSAPP_ORDER_RECIPIENT is not configured."
        )
        message_record.save(
            update_fields=["status", "error_message"]
        )
        return message_record

    if not settings.WHATSAPP_API_URL:
        message_record.status = WhatsAppMessage.STATUS_FAILED
        message_record.error_message = (
            "WHATSAPP_API_URL is not configured."
        )
        message_record.save(
            update_fields=["status", "error_message"]
        )
        return message_record

    if not settings.WHATSAPP_ACCESS_TOKEN:
        message_record.status = WhatsAppMessage.STATUS_FAILED
        message_record.error_message = (
            "WHATSAPP_ACCESS_TOKEN is not configured."
        )
        message_record.save(
            update_fields=["status", "error_message"]
        )
        return message_record

    headers = {
        "Authorization": (
            f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"
        ),
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "text",
        "text": {
            "body": message_body,
        },
    }

    try:
        response = requests.post(
            settings.WHATSAPP_API_URL,
            headers=headers,
            json=payload,
            timeout=15,
        )
        response.raise_for_status()

        response_data = response.json()

        provider_message_id = ""

        messages = response_data.get("messages", [])

        if messages:
            provider_message_id = messages[0].get("id", "")

        message_record.status = WhatsAppMessage.STATUS_SENT
        message_record.provider_message_id = provider_message_id
        message_record.sent_at = timezone.now()
        message_record.error_message = ""

        message_record.save(
            update_fields=[
                "status",
                "provider_message_id",
                "sent_at",
                "error_message",
            ]
        )

    except requests.RequestException as error:
        logger.exception(
            "WhatsApp sending failed for order %s",
            order.order_number,
        )

        response_text = ""

        if getattr(error, "response", None) is not None:
            response_text = error.response.text[:1000]

        message_record.status = WhatsAppMessage.STATUS_FAILED
        message_record.error_message = (
            response_text or str(error)
        )

        message_record.save(
            update_fields=["status", "error_message"]
        )

    except ValueError as error:
        message_record.status = WhatsAppMessage.STATUS_FAILED
        message_record.error_message = (
            f"Invalid provider response: {error}"
        )

        message_record.save(
            update_fields=["status", "error_message"]
        )

    return message_record
