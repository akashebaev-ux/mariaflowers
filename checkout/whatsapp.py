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
