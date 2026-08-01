import json
import logging
import time

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.http import HttpResponse
from django.template.loader import render_to_string

from products.models import Product
from profiles.models import UserProfile

from .models import Order, OrderLineItem


logger = logging.getLogger(__name__)


class StripeWH_Handler:
    """Handle Stripe webhooks."""

    def __init__(self, request):
        self.request = request

    def _send_confirmation_email(self, order):
        """Send the customer an order confirmation email."""
        subject = render_to_string(
            "checkout/confirmation_emails/"
            "confirmation_email_subject.txt",
            {
                "order": order,
            },
        ).strip()

        body = render_to_string(
            "checkout/confirmation_emails/"
            "confirmation_email_body.txt",
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

    def handle_event(self, event):
        """Handle a generic or unexpected webhook event."""
        return HttpResponse(
            content=(
                f'Unhandled webhook received: '
                f'{event["type"]}'
            ),
            status=200,
        )

    def handle_payment_intent_succeeded(self, event):
        """Handle a successful Stripe PaymentIntent webhook."""

        # Get the Stripe PaymentIntent.
        intent = event.data.object
        pid = intent.id

        # Convert Stripe metadata to a normal Python dictionary.
        metadata = dict(intent.metadata)

        bag = metadata.get("bag", "{}")
        save_info = metadata.get("save_info", "")
        username = metadata.get(
            "username",
            "AnonymousUser",
        )

        try:
            charge = intent.charges.data[0]
            billing_details = charge.billing_details
            shipping_details = intent.shipping

        except (IndexError, AttributeError) as error:
            logger.exception(
                "Missing payment or shipping details: %s",
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

        grand_total = round(charge.amount / 100, 2)

        address = shipping_details.address.to_dict()

        # Convert blank Stripe address values into None.
        for field, value in address.items():
            if value == "":
                address[field] = None

        profile = None

        # Attach the authenticated user's profile where available.
        if username != "AnonymousUser":
            try:
                user = User.objects.get(username=username)

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
                    "Could not update user profile for %s: %s",
                    username,
                    error,
                )

        order_exists = False
        order = None
        attempt = 1

        # The checkout view normally creates the order.
        # Wait briefly in case the webhook arrives first.
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

        # If checkout already created the order, send its email.
        if order_exists:
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
                    "SUCCESS: Verified existing order and "
                    "sent confirmation email"
                ),
                status=200,
            )

        # If checkout did not create the order, create it here.
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

            for item_id, item_data in bag_data.items():
                product = Product.objects.get(id=item_id)

                # Original simple bag format:
                # {"10": 2}
                if isinstance(item_data, int):
                    OrderLineItem.objects.create(
                        order=order,
                        product=product,
                        quantity=item_data,
                        extra_flowers=0,
                    )

                # Dictionary-based bag formats.
                elif isinstance(item_data, dict):

                    # Current Maria Flowers format:
                    # {
                    #     "10": {
                    #         "items_by_customisation": {
                    #             "5": 1
                    #         }
                    #     }
                    # }
                    if "items_by_customisation" in item_data:
                        customisations = item_data[
                            "items_by_customisation"
                        ]

                        for extra_flowers, quantity in (
                            customisations.items()
                        ):
                            OrderLineItem.objects.create(
                                order=order,
                                product=product,
                                quantity=int(quantity),
                                extra_flowers=int(
                                    extra_flowers
                                ),
                            )

                    # Alternative supported format:
                    # {
                    #     "10": {
                    #         "quantity": 1,
                    #         "extra_flowers": 5
                    #     }
                    else:
                        quantity = int(
                            item_data.get("quantity", 1)
                        )
                        extra_flowers = int(
                            item_data.get(
                                "extra_flowers",
                                0,
                            )
                        )

                        OrderLineItem.objects.create(
                            order=order,
                            product=product,
                            quantity=quantity,
                            extra_flowers=extra_flowers,
                        )

                else:
                    raise ValueError(
                        "Invalid shopping bag item format."
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
                "SUCCESS: Created order and sent "
                "confirmation email"
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
                f'Webhook received: '
                f'{event["type"]}'
            ),
            status=200,
        )
