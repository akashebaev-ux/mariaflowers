import logging

import stripe

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from checkout.webhook_handler import StripeWH_Handler


logger = logging.getLogger(__name__)


@require_POST
@csrf_exempt
def webhook(request):
    """Listen for Stripe webhooks."""

    webhook_secret = settings.STRIPE_WH_SECRET
    stripe.api_key = settings.STRIPE_SECRET_KEY

    payload = request.body
    signature_header = request.META.get(
        "HTTP_STRIPE_SIGNATURE"
    )

    if not signature_header:
        logger.error(
            "Stripe webhook received without a signature header."
        )
        return HttpResponse(
            content="Missing Stripe signature.",
            status=400,
        )

    if not webhook_secret:
        logger.error(
            "STRIPE_WH_SECRET is missing from settings."
        )
        return HttpResponse(
            content="Stripe webhook secret is missing.",
            status=500,
        )

    try:
        event = stripe.Webhook.construct_event(
            payload,
            signature_header,
            webhook_secret,
        )

    except ValueError as error:
        logger.exception(
            "Invalid Stripe webhook payload: %s",
            error,
        )
        return HttpResponse(
            content=f"Invalid payload: {error}",
            status=400,
        )

    except stripe.error.SignatureVerificationError as error:
        logger.exception(
            "Invalid Stripe webhook signature: %s",
            error,
        )
        return HttpResponse(
            content=f"Invalid signature: {error}",
            status=400,
        )

    except Exception as error:
        logger.exception(
            "Unexpected Stripe webhook verification error: %s",
            error,
        )
        return HttpResponse(
            content=(
                "Unexpected webhook verification error: "
                f"{type(error).__name__}: {error}"
            ),
            status=400,
        )

    handler = StripeWH_Handler(request)

    event_map = {
        "payment_intent.succeeded": (
            handler.handle_payment_intent_succeeded
        ),
        "payment_intent.payment_failed": (
            handler.handle_payment_intent_payment_failed
        ),
    }

    event_type = event["type"]

    event_handler = event_map.get(
        event_type,
        handler.handle_event,
    )

    try:
        return event_handler(event)

    except Exception as error:
        logger.exception(
            "Unhandled Stripe webhook error for event %s",
            event_type,
        )

        return HttpResponse(
            content=(
                f"Unhandled webhook error for {event_type}: "
                f"{type(error).__name__}: {error}"
            ),
            status=500,
        )
