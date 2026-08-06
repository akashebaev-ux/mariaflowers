import json
import logging
import time

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import transaction
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone

from products.models import Product
from profiles.models import UserProfile

from .models import (
    ORDER_STATUS_PREPARING,
    Order,
    OrderLineItem,
)
from .whatsapp import send_paid_order_whatsapp


logger = logging.getLogger(__name__)

MAX_GREETING_MESSAGE_LENGTH = 250


class StripeWH_Handler:
    """Handle Stripe webhooks."""

    def __init__(self, request):
        self.request = request

    def _send_confirmation_email(self, order):
        """Send the customer an order confirmation email."""

        subject = render_to_string(
            (
                "checkout/confirmation_emails/"
                "confirmation_email_subject.txt"
            ),
            {"order": order},
        ).strip()

        body = render_to_string(
            (
                "checkout/confirmation_emails/"
                "confirmation_email_body.txt"
            ),
            {
                "order": order,
                "contact_email": settings.DEFAULT_FROM_EMAIL,
            },
        )

        return send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [order.email],
            fail_silently=False,
        )

    def _clean_greeting_message(
        self,
        product,
        greeting_message,
    ):
        """Validate and clean a greeting-card message."""

        greeting_message = str(
            greeting_message or ""
        ).strip()

        if not product.allows_greeting_message:
            return ""

        return greeting_message[
            :MAX_GREETING_MESSAGE_LENGTH
        ]

    def _create_order_line_item(
        self,
        order,
        product,
        quantity,
        extra_flowers=0,
        greeting_message="",
    ):
        """Create one order line item from shopping-bag data."""

        quantity = int(quantity)
        extra_flowers = int(extra_flowers)

        if quantity < 1:
            raise ValueError(
                "Order line quantity must be at least 1."
            )

        extra_flowers = max(
            0,
            min(
                extra_flowers,
                product.max_extra_flowers,
            ),
        )

        greeting_message = self._clean_greeting_message(
            product,
            greeting_message,
        )

        OrderLineItem.objects.create(
            order=order,
            product=product,
            quantity=quantity,
            extra_flowers=extra_flowers,
            greeting_message=greeting_message,
        )

    def _create_order_line_items(
        self,
        order,
        bag_data,
    ):
        """
        Create all order line items from saved bag data.

        Supports old integer bag items, customised products,
        sized products, and greeting-card messages.
        """

        for item_id, item_data in bag_data.items():
            product = Product.objects.get(id=item_id)

            # Old/simple format:
            # {
            #     "10": 2
            # }
            if isinstance(item_data, int):
                self._create_order_line_item(
                    order=order,
                    product=product,
                    quantity=item_data,
                )
                continue

            if not isinstance(item_data, dict):
                raise ValueError(
                    "Invalid shopping bag item format."
                )

            # Current customisation format:
            # {
            #     "10": {
            #         "items_by_customisation": {
            #             "0": {
            #                 "quantity": 1,
            #                 "greeting_message": "Happy birthday!"
            #             }
            #         }
            #     }
            # }
            if "items_by_customisation" in item_data:
                customisations = item_data[
                    "items_by_customisation"
                ]

                for extra_flowers, line_data in (
                    customisations.items()
                ):
                    if isinstance(line_data, dict):
                        quantity = line_data.get(
                            "quantity",
                            1,
                        )
                        greeting_message = line_data.get(
                            "greeting_message",
                            "",
                        )
                    else:
                        quantity = line_data
                        greeting_message = ""

                    self._create_order_line_item(
                        order=order,
                        product=product,
                        quantity=quantity,
                        extra_flowers=extra_flowers,
                        greeting_message=greeting_message,
                    )

                continue

            # Sized product format:
            # {
            #     "10": {
            #         "items_by_size": {
            #             "m": {
            #                 "0": {
            #                     "quantity": 1,
            #                     "greeting_message": ""
            #                 }
            #             }
            #         }
            #     }
            # }
            if "items_by_size" in item_data:
                items_by_size = item_data[
                    "items_by_size"
                ]

                for size, customisations in (
                    items_by_size.items()
                ):
                    for extra_flowers, line_data in (
                        customisations.items()
                    ):
                        if isinstance(line_data, dict):
                            quantity = line_data.get(
                                "quantity",
                                1,
                            )
                            greeting_message = (
                                line_data.get(
                                    "greeting_message",
                                    "",
                                )
                            )
                        else:
                            quantity = line_data
                            greeting_message = ""

                        self._create_order_line_item(
                            order=order,
                            product=product,
                            quantity=quantity,
                            extra_flowers=extra_flowers,
                            greeting_message=(
                                greeting_message
                            ),
                        )

                continue

            # Alternative dictionary format:
            # {
            #     "10": {
            #         "quantity": 1,
            #         "extra_flowers": 5,
            #         "greeting_message": "Happy birthday!"
            #     }
            # }
            quantity = item_data.get(
                "quantity",
                1,
            )

            extra_flowers = item_data.get(
                "extra_flowers",
                0,
            )

            greeting_message = item_data.get(
                "greeting_message",
                "",
            )

            self._create_order_line_item(
                order=order,
                product=product,
                quantity=quantity,
                extra_flowers=extra_flowers,
                greeting_message=greeting_message,
            )

    def handle_event(self, event):
        """Handle a generic or unexpected webhook event."""

        return HttpResponse(
            content=(
                f'Unhandled webhook received: {event["type"]}'
            ),
            status=200,
        )

    def handle_payment_intent_succeeded(self, event):
        """Handle a successful Stripe PaymentIntent webhook."""

        intent = event.data.object
        pid = intent.id

        metadata = intent.metadata

        bag = (
            metadata["bag"]
            if "bag" in metadata
            else "{}"
        )

        save_info = (
            metadata["save_info"]
            if "save_info" in metadata
            else ""
        )

        username = (
            metadata["username"]
            if "username" in metadata
            else "AnonymousUser"
        )

        try:
            charge = intent.charges.data[0]
            billing_details = charge.billing_details
            shipping_details = intent.shipping

        except (IndexError, AttributeError) as error:
            logger.exception(
                "Missing Stripe charge or shipping details: %s",
                error,
            )

            return HttpResponse(
                content=(
                    f'Webhook received: {event["type"]} | '
                    "ERROR: Missing charge or shipping details"
                ),
                status=500,
            )

        if not shipping_details:
            logger.error(
                "Shipping details are missing for PaymentIntent %s",
                pid,
            )

            return HttpResponse(
                content=(
                    f'Webhook received: {event["type"]} | '
                    "ERROR: Shipping details are missing"
                ),
                status=500,
            )

        grand_total = round(
            charge.amount / 100,
            2,
        )

        address = shipping_details.address.to_dict()

        for field, value in address.items():
            if value == "":
                address[field] = None

        profile = None

        if username != "AnonymousUser":
            try:
                user = User.objects.get(
                    username=username
                )

                profile, created = (
                    UserProfile.objects.get_or_create(
                        user=user
                    )
                )

                should_save_info = str(
                    save_info
                ).lower() in {
                    "true",
                    "on",
                    "1",
                    "yes",
                }

                if should_save_info:
                    profile.default_phone_number = (
                        shipping_details.phone
                    )
                    profile.default_country = address.get(
                        "country"
                    )
                    profile.default_postcode = address.get(
                        "postal_code"
                    )
                    profile.default_town_or_city = address.get(
                        "city"
                    )
                    profile.default_street_address1 = (
                        address.get("line1")
                    )
                    profile.default_street_address2 = (
                        address.get("line2")
                    )
                    profile.default_county = address.get(
                        "state"
                    )
                    profile.save()

            except User.DoesNotExist:
                profile = None

            except Exception as error:
                logger.exception(
                    "Could not update profile for user %s: %s",
                    username,
                    error,
                )

        order_exists = False
        order = None
        attempt = 1

        while attempt <= 5:
            try:
                order = Order.objects.get(
                    full_name__iexact=shipping_details.name,
                    email__iexact=billing_details.email,
                    phone_number__iexact=(
                        shipping_details.phone
                    ),
                    country__iexact=address.get("country"),
                    postcode__iexact=address.get(
                        "postal_code"
                    ),
                    town_or_city__iexact=address.get(
                        "city"
                    ),
                    street_address1__iexact=address.get(
                        "line1"
                    ),
                    street_address2__iexact=address.get(
                        "line2"
                    ),
                    county__iexact=address.get("state"),
                    grand_total=grand_total,
                    original_bag=bag,
                    stripe_pid=pid,
                )

                order_exists = True
                break

            except Order.DoesNotExist:
                attempt += 1
                time.sleep(1)

            except Exception as error:
                logger.exception(
                    "Order lookup failed for PaymentIntent %s: %s",
                    pid,
                    error,
                )

                return HttpResponse(
                    content=(
                        f'Webhook received: {event["type"]} | '
                        f"ORDER LOOKUP ERROR: {error}"
                    ),
                    status=500,
                )

        if order_exists:
            if not order.is_paid:
                order.is_paid = True
                order.paid_at = timezone.now()
                order.status = ORDER_STATUS_PREPARING
                order.save(
                    update_fields=[
                        "is_paid",
                        "paid_at",
                        "status",
                    ]
                )

            transaction.on_commit(
                lambda order=order: (
                    send_paid_order_whatsapp(order)
                )
            )

            try:
                self._send_confirmation_email(order)

            except Exception as error:
                logger.exception(
                    "Email failed for existing order %s: %s",
                    order.order_number,
                    error,
                )

                return HttpResponse(
                    content=(
                        f'Webhook received: {event["type"]} | '
                        f"EMAIL ERROR: {error}"
                    ),
                    status=500,
                )

            return HttpResponse(
                content=(
                    f'Webhook received: {event["type"]} | '
                    "SUCCESS: Verified existing order, "
                    "sent WhatsApp notification and "
                    "sent confirmation email"
                ),
                status=200,
            )

        try:
            order = Order.objects.create(
                full_name=shipping_details.name,
                user_profile=profile,
                email=billing_details.email,
                phone_number=shipping_details.phone,
                country=address.get("country"),
                postcode=address.get("postal_code"),
                town_or_city=address.get("city"),
                street_address1=address.get("line1"),
                street_address2=address.get("line2"),
                county=address.get("state"),
                grand_total=grand_total,
                original_bag=bag,
                stripe_pid=pid,
            )

            bag_data = json.loads(bag)

            self._create_order_line_items(
                order=order,
                bag_data=bag_data,
            )

            order.is_paid = True
            order.paid_at = timezone.now()
            order.status = ORDER_STATUS_PREPARING
            order.save(
                update_fields=[
                    "is_paid",
                    "paid_at",
                    "status",
                ]
            )

            transaction.on_commit(
                lambda order=order: (
                    send_paid_order_whatsapp(order)
                )
            )

        except Exception as error:
            logger.exception(
                "Could not create order for PaymentIntent %s: %s",
                pid,
                error,
            )

            if order:
                order.delete()

            return HttpResponse(
                content=(
                    f'Webhook received: {event["type"]} | '
                    f"ORDER ERROR: {error}"
                ),
                status=500,
            )

        try:
            self._send_confirmation_email(order)

        except Exception as error:
            logger.exception(
                "Email failed for new order %s: %s",
                order.order_number,
                error,
            )

            return HttpResponse(
                content=(
                    f'Webhook received: {event["type"]} | '
                    f"EMAIL ERROR: {error}"
                ),
                status=500,
            )

        return HttpResponse(
            content=(
                f'Webhook received: {event["type"]} | '
                "SUCCESS: Created order, sent WhatsApp "
                "notification and sent confirmation email"
            ),
            status=200,
        )

    def handle_payment_intent_payment_failed(
        self,
        event,
    ):
        """Handle a failed Stripe PaymentIntent."""

        return HttpResponse(
            content=(
                f'Webhook received: {event["type"]}'
            ),
            status=200,
        )
