import logging

import requests
from django.conf import settings


logger = logging.getLogger(__name__)


def send_whatsapp_template(recipient):
    """Send a WhatsApp template message using Meta Cloud API."""

    if not settings.WHATSAPP_API_URL:
        logger.error("WHATSAPP_API_URL is not configured.")
        return False

    if not settings.WHATSAPP_ACCESS_TOKEN:
        logger.error("WHATSAPP_ACCESS_TOKEN is not configured.")
        return False

    headers = {
        "Authorization": (
            f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"
        ),
        "Content-Type": "application/json",
    }

    data = {
        "messaging_product": "whatsapp",
        "to": "787029087217",
        "type": "template",
        "template": {
            "name": "jaspers_market_order_confirmation_v1",
            "language": {
                "code": "en_US",
            },
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {
                            "type": "text",
                            "text": "John Doe",
                        },
                        {
                            "type": "text",
                            "text": "123456",
                        },
                        {
                            "type": "text",
                            "text": "Aug 18, 2026",
                        },
                    ],
                }
            ],
        },
    }

    try:
        response = requests.post(
            settings.WHATSAPP_API_URL,
            headers=headers,
            json=data,
            timeout=10,
        )

        print(
            "WhatsApp status:",
            response.status_code,
        )

        print(
            "WhatsApp response:",
            response.text,
        )

        response.raise_for_status()

        return True

    except requests.RequestException as error:
        logger.error(
            "WhatsApp API request failed: %s",
            error,
        )

        if error.response is not None:
            logger.error(
                "WhatsApp API response: %s",
                error.response.text,
            )

        return False
