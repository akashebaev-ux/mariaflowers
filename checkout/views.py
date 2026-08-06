import json

import stripe

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
    reverse,
)
from django.views.decorators.http import (
    require_http_methods,
    require_POST,
)

from bag.contexts import bag_contents
from products.models import Product
from profiles.forms import UserProfileForm
from profiles.models import UserProfile

from .forms import (
    OrderForm,
    ReviewForm,
    ReviewImageForm,
)
from .models import (
    Order,
    OrderLineItem,
    Review,
    ReviewReaction,
)


@require_POST
def cache_checkout_data(request):
    """Store bag and checkout details in Stripe metadata."""

    try:
        client_secret = request.POST.get(
            "client_secret",
            "",
        )
        pid = client_secret.split("_secret")[0]

        stripe.api_key = settings.STRIPE_SECRET_KEY

        stripe.PaymentIntent.modify(
            pid,
            metadata={
                "bag": json.dumps(
                    request.session.get("bag", {})
                ),
                "save_info": request.POST.get(
                    "save_info",
                    "",
                ),
                "username": str(request.user),
            },
        )

        return HttpResponse(status=200)

    except Exception as error:
        messages.error(
            request,
            "Sorry, your payment cannot be processed right now. "
            "Please try again later.",
        )

        return HttpResponse(
            content=str(error),
            status=400,
        )


def _create_order_line_item(
    order,
    product,
    quantity,
    extra_flowers=0,
    greeting_message="",
):
    """Create and save one order line item."""

    quantity = int(quantity)
    extra_flowers = int(extra_flowers)

    greeting_message = str(
        greeting_message or ""
    ).strip()

    if len(greeting_message) > 250:
        greeting_message = greeting_message[:250]

    if not product.allows_greeting_message:
        greeting_message = ""

    order_line_item = OrderLineItem(
        order=order,
        product=product,
        quantity=quantity,
        extra_flowers=extra_flowers,
        greeting_message=greeting_message,
    )

    order_line_item.save()


def _create_order_line_items(order, bag):
    """
    Create all order line items from the shopping bag.

    Supports:
    - old integer bag entries
    - items grouped by customisation
    - items grouped by size
    - greeting-card messages
    """

    for item_id, item_data in bag.items():
        product = Product.objects.get(id=item_id)

        if isinstance(item_data, int):
            _create_order_line_item(
                order=order,
                product=product,
                quantity=item_data,
            )
            continue

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

                _create_order_line_item(
                    order=order,
                    product=product,
                    quantity=quantity,
                    extra_flowers=extra_flowers,
                    greeting_message=greeting_message,
                )

            continue

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

                    _create_order_line_item(
                        order=order,
                        product=product,
                        quantity=quantity,
                        extra_flowers=extra_flowers,
                        greeting_message=(
                            greeting_message
                        ),
                    )

            continue

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

        _create_order_line_item(
            order=order,
            product=product,
            quantity=quantity,
            extra_flowers=extra_flowers,
            greeting_message=greeting_message,
        )


def checkout(request):
    """Create and process an order."""

    stripe_public_key = settings.STRIPE_PUBLIC_KEY
    stripe_secret_key = settings.STRIPE_SECRET_KEY

    if request.method == "POST":
        bag = request.session.get("bag", {})

        if not bag:
            messages.error(
                request,
                "There's nothing in your bag at the moment.",
            )
            return redirect(reverse("products"))

        form_data = {
            "full_name": request.POST.get(
                "full_name",
                "",
            ),
            "email": request.POST.get(
                "email",
                "",
            ),
            "phone_number": request.POST.get(
                "phone_number",
                "",
            ),
            "country": request.POST.get(
                "country",
                "",
            ),
            "postcode": request.POST.get(
                "postcode",
                "",
            ),
            "town_or_city": request.POST.get(
                "town_or_city",
                "",
            ),
            "street_address1": request.POST.get(
                "street_address1",
                "",
            ),
            "street_address2": request.POST.get(
                "street_address2",
                "",
            ),
            "county": request.POST.get(
                "county",
                "",
            ),
        }

        order_form = OrderForm(form_data)

        if order_form.is_valid():
            order = order_form.save(commit=False)

            delivery_details = request.session.get(
                "delivery_details",
                {},
            )

            if not delivery_details:
                messages.error(
                    request,
                    "Please select a delivery date and time.",
                )
                return redirect(reverse("view_bag"))

            order.delivery_date = delivery_details.get(
                "delivery_date"
            )

            order.delivery_time = delivery_details.get(
                "delivery_time"
            )

            client_secret = request.POST.get(
                "client_secret",
                "",
            )
            pid = client_secret.split("_secret")[0]

            order.stripe_pid = pid
            order.original_bag = json.dumps(bag)
            order.save()

            try:
                _create_order_line_items(
                    order=order,
                    bag=bag,
                )

            except Product.DoesNotExist:
                messages.error(
                    request,
                    "One of the products in your bag wasn't "
                    "found in our database. Please call us "
                    "for assistance!",
                )

                order.delete()
                return redirect(reverse("view_bag"))

            except (
                TypeError,
                ValueError,
                AttributeError,
            ):
                messages.error(
                    request,
                    "There was a problem reading one of the "
                    "items in your bag. Please remove it and "
                    "add it again.",
                )

                order.delete()
                return redirect(reverse("view_bag"))

            request.session["save_info"] = (
                "save-info" in request.POST
            )

            return redirect(
                reverse(
                    "checkout_success",
                    args=[order.order_number],
                )
            )

        messages.error(
            request,
            "There was an error with your form. "
            "Please double-check your information.",
        )

    else:
        bag = request.session.get("bag", {})

        if not bag:
            messages.error(
                request,
                "There's nothing in your bag at the moment.",
            )
            return redirect(reverse("products"))

        current_bag = bag_contents(request)
        total = current_bag["grand_total"]
        stripe_total = round(total * 100)

        stripe.api_key = stripe_secret_key

        intent = stripe.PaymentIntent.create(
            amount=stripe_total,
            currency=settings.STRIPE_CURRENCY,
        )

        if request.user.is_authenticated:
            try:
                profile = UserProfile.objects.get(
                    user=request.user
                )

                order_form = OrderForm(
                    initial={
                        "full_name": (
                            profile.user.get_full_name()
                        ),
                        "email": profile.user.email,
                        "phone_number": (
                            profile.default_phone_number
                        ),
                        "country": (
                            profile.default_country
                        ),
                        "postcode": (
                            profile.default_postcode
                        ),
                        "town_or_city": (
                            profile.default_town_or_city
                        ),
                        "street_address1": (
                            profile.default_street_address1
                        ),
                        "street_address2": (
                            profile.default_street_address2
                        ),
                        "county": (
                            profile.default_county
                        ),
                    }
                )

            except UserProfile.DoesNotExist:
                order_form = OrderForm()

        else:
            order_form = OrderForm()

        if not stripe_public_key:
            messages.warning(
                request,
                "Stripe public key is missing. "
                "Did you forget to set it in your environment?",
            )

        template = "checkout/checkout.html"

        context = {
            "order_form": order_form,
            "stripe_public_key": stripe_public_key,
            "client_secret": intent.client_secret,
        }

        return render(
            request,
            template,
            context,
        )

    template = "checkout/checkout.html"

    context = {
        "order_form": order_form,
        "stripe_public_key": stripe_public_key,
        "client_secret": request.POST.get(
            "client_secret",
            "",
        ),
    }

    return render(
        request,
        template,
        context,
    )


def checkout_success(request, order_number):
    """Handle successful checkouts."""

    save_info = request.session.get("save_info")

    order = get_object_or_404(
        Order,
        order_number=order_number,
    )

    if request.user.is_authenticated:
        try:
            profile = UserProfile.objects.get(
                user=request.user
            )

            order.user_profile = profile
            order.save()

            if save_info:
                profile_data = {
                    "default_phone_number": (
                        order.phone_number
                    ),
                    "default_country": order.country,
                    "default_postcode": order.postcode,
                    "default_town_or_city": (
                        order.town_or_city
                    ),
                    "default_street_address1": (
                        order.street_address1
                    ),
                    "default_street_address2": (
                        order.street_address2
                    ),
                    "default_county": order.county,
                }

                user_profile_form = UserProfileForm(
                    profile_data,
                    instance=profile,
                )

                if user_profile_form.is_valid():
                    user_profile_form.save()

        except UserProfile.DoesNotExist:
            pass

    messages.success(
        request,
        (
            f"Order successfully processed! "
            f"Your order number is {order_number}. "
            f"A confirmation email will be sent to "
            f"{order.email}."
        ),
    )
    if "bag" in request.session:
        del request.session["bag"]

    if "delivery_details" in request.session:
        del request.session["delivery_details"]

    template = "checkout/checkout_success.html"

    context = {
        "order": order,
    }

    return render(
        request,
        template,
        context,
    )


@login_required
@require_http_methods(["GET", "POST"])
def submit_review(request, order_number):
    """Allow a customer to review one completed order."""

    order = get_object_or_404(
        Order,
        order_number=order_number,
        user_profile__user=request.user,
    )

    if not order.is_completed:
        messages.error(
            request,
            "You can review this order after it has been completed.",
        )
        return redirect(
            reverse(
                "order_history",
                args=[order.order_number],
            )
        )

    if hasattr(order, "review"):
        messages.info(
            request,
            "You have already reviewed this order.",
        )
        return redirect(
            reverse(
                "order_history",
                args=[order.order_number],
            )
        )

    if request.method == "POST":
        review_form = ReviewForm(request.POST)
        image_form = ReviewImageForm(
            request.POST,
            request.FILES,
        )

        if review_form.is_valid() and image_form.is_valid():
            try:
                with transaction.atomic():
                    review = review_form.save(commit=False)
                    review.order = order
                    review.save()

                    review_image = image_form.save(commit=False)

                    if review_image.image:
                        review_image.review = review
                        review_image.save()

            except IntegrityError:
                messages.error(
                    request,
                    "A review has already been submitted "
                    "for this order.",
                )
                return redirect(
                    reverse(
                        "order_history",
                        args=[order.order_number],
                    )
                )

            messages.success(
                request,
                "Thank you! Your review has been submitted.",
            )
            return redirect(
                reverse(
                    "order_history",
                    args=[order.order_number],
                )
            )

    else:
        review_form = ReviewForm()
        image_form = ReviewImageForm()

    template = "checkout/submit_review.html"

    context = {
        "order": order,
        "review_form": review_form,
        "image_form": image_form,
    }

    return render(
        request,
        template,
        context,
    )


@login_required
@require_POST
def toggle_review_reaction(request, review_id):
    """Add or remove the current customer's helpful reaction."""

    review = get_object_or_404(
        Review,
        pk=review_id,
    )

    profile = get_object_or_404(
        UserProfile,
        user=request.user,
    )

    reaction = ReviewReaction.objects.filter(
        review=review,
        user_profile=profile,
    ).first()

    if reaction:
        reaction.delete()
        messages.info(
            request,
            "Helpful reaction removed.",
        )
    else:
        ReviewReaction.objects.create(
            review=review,
            user_profile=profile,
        )
        messages.success(
            request,
            "You marked this review as helpful.",
        )

    return redirect(
        reverse(
            "order_history",
            args=[review.order.order_number],
        )
    )
