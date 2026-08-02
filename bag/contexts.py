from decimal import Decimal

from django.conf import settings
from django.shortcuts import get_object_or_404

from products.models import Product


def _get_line_data(line_data):
    """
    Extract quantity and greeting message from one bag line.

    Older bag sessions may store the quantity directly as an integer.
    New bag sessions store a dictionary containing quantity and message.
    """

    if isinstance(line_data, dict):
        quantity = int(line_data.get("quantity", 0))
        greeting_message = line_data.get(
            "greeting_message",
            "",
        )
    else:
        quantity = int(line_data)
        greeting_message = ""

    return quantity, greeting_message


def _prepare_bag_item(
    item_id,
    product,
    quantity,
    extra_flowers=0,
    greeting_message="",
    size=None,
):
    """Prepare one product line and calculate its prices."""

    extra_flowers = max(
        0,
        min(
            int(extra_flowers),
            product.max_extra_flowers,
        ),
    )

    customised_unit_price = (
        product.price
        + (
            product.extra_flower_price
            * extra_flowers
        )
    )

    subtotal = customised_unit_price * quantity

    bag_item = {
        "item_id": item_id,
        "quantity": quantity,
        "product": product,
        "extra_flowers": extra_flowers,
        "total_flowers": (
            product.included_flower_count
            + extra_flowers
        ),
        "customised_unit_price": customised_unit_price,
        "subtotal": subtotal,
        "greeting_message": greeting_message,
    }

    if size:
        bag_item["size"] = size

    return bag_item


def bag_contents(request):
    """Return shopping bag items and calculated totals."""

    bag_items = []
    total = Decimal("0.00")
    product_count = 0

    bag = request.session.get("bag", {})

    for item_id, item_data in bag.items():
        product = get_object_or_404(
            Product,
            pk=item_id,
        )

        if isinstance(item_data, dict) and (
            "items_by_customisation" in item_data
        ):
            customisations = item_data[
                "items_by_customisation"
            ]

            for extra_flowers, line_data in (
                customisations.items()
            ):
                quantity, greeting_message = (
                    _get_line_data(line_data)
                )

                if quantity <= 0:
                    continue

                bag_item = _prepare_bag_item(
                    item_id=item_id,
                    product=product,
                    quantity=quantity,
                    extra_flowers=extra_flowers,
                    greeting_message=greeting_message,
                )

                total += bag_item["subtotal"]
                product_count += quantity
                bag_items.append(bag_item)

        elif isinstance(item_data, dict) and (
            "items_by_size" in item_data
        ):
            items_by_size = item_data[
                "items_by_size"
            ]

            for size, customisations in (
                items_by_size.items()
            ):
                for extra_flowers, line_data in (
                    customisations.items()
                ):
                    quantity, greeting_message = (
                        _get_line_data(line_data)
                    )

                    if quantity <= 0:
                        continue

                    bag_item = _prepare_bag_item(
                        item_id=item_id,
                        product=product,
                        quantity=quantity,
                        extra_flowers=extra_flowers,
                        greeting_message=greeting_message,
                        size=size,
                    )

                    total += bag_item["subtotal"]
                    product_count += quantity
                    bag_items.append(bag_item)

        elif isinstance(item_data, int):
            # Compatibility with old bag session data.
            quantity = int(item_data)

            if quantity <= 0:
                continue

            bag_item = _prepare_bag_item(
                item_id=item_id,
                product=product,
                quantity=quantity,
            )

            total += bag_item["subtotal"]
            product_count += quantity
            bag_items.append(bag_item)

    free_delivery_threshold = Decimal(
        str(settings.FREE_DELIVERY_THRESHOLD)
    )

    delivery_percentage = Decimal(
        str(settings.STANDARD_DELIVERY_PERCENTAGE)
    )

    if total < free_delivery_threshold:
        delivery = (
            total
            * delivery_percentage
            / Decimal("100")
        )

        free_delivery_delta = (
            free_delivery_threshold
            - total
        )
    else:
        delivery = Decimal("0.00")
        free_delivery_delta = Decimal("0.00")

    grand_total = total + delivery

    context = {
        "bag_items": bag_items,
        "total": total,
        "product_count": product_count,
        "delivery": delivery,
        "free_delivery_delta": free_delivery_delta,
        "free_delivery_threshold": free_delivery_threshold,
        "grand_total": grand_total,
    }

    return context
