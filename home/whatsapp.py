import logging

import requests
from django.conf import settings


logger = logging.getLogger(__name__)


def send_whatsapp_message(recipient, message):
    """Send a WhatsApp text message using Meta Cloud API."""

    if not settings.WHATSAPP_API_URL:
        logger.error("WHATSAPP_API_URL is not configured.")
        return False

    if not settings.WHATSAPP_ACCESS_TOKEN:
        logger.error("WHATSAPP_ACCESS_TOKEN is not configured.")
        return False

    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    data = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "text",
        "text": {
            "body": message,
        },
    }

    try:
        response = requests.post(
            settings.WHATSAPP_API_URL,
            headers=headers,
            json=data,
            timeout=10,
        )

        response.raise_for_status()

        print("WhatsApp response:", response.json())

        return True

    except requests.RequestException as error:
        print("WhatsApp error:", error)

        if error.response is not None:
            print(
                "WhatsApp API response:",
                error.response.text,
            )

        return False
