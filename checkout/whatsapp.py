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
