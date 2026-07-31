from decimal import Decimal

from django.conf import settings
from django.shortcuts import get_object_or_404

from products.models import Product


def bag_contents(request):
    """Return shopping bag items and calculated totals."""

    bag_items = []
    total = Decimal("0.00")
    product_count = 0

    bag = request.session.get("bag", {})

    for item_id, item_data in bag.items():
        product = get_object_or_404(Product, pk=item_id)

        if "items_by_customisation" in item_data:
            customisations = item_data["items_by_customisation"]

            for extra_flowers, quantity in customisations.items():
                extra_flowers = int(extra_flowers)
                quantity = int(quantity)

                extra_flowers = max(
                    0,
                    min(
                        extra_flowers,
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

                total += subtotal
                product_count += quantity

                bag_items.append({
                    "item_id": item_id,
                    "quantity": quantity,
                    "product": product,
                    "extra_flowers": extra_flowers,
                    "total_flowers": (
                        product.included_flower_count
                        + extra_flowers
                    ),
                    "customised_unit_price":
                        customised_unit_price,
                    "subtotal": subtotal,
                })

        elif "items_by_size" in item_data:
            for size, customisations in (
                item_data["items_by_size"].items()
            ):
                for extra_flowers, quantity in (
                    customisations.items()
                ):
                    extra_flowers = int(extra_flowers)
                    quantity = int(quantity)

                    extra_flowers = max(
                        0,
                        min(
                            extra_flowers,
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

                    subtotal = (
                        customised_unit_price
                        * quantity
                    )

                    total += subtotal
                    product_count += quantity

                    bag_items.append({
                        "item_id": item_id,
                        "quantity": quantity,
                        "product": product,
                        "size": size,
                        "extra_flowers": extra_flowers,
                        "total_flowers": (
                            product.included_flower_count
                            + extra_flowers
                        ),
                        "customised_unit_price":
                            customised_unit_price,
                        "subtotal": subtotal,
                    })

        elif isinstance(item_data, int):
            # Temporary compatibility with old session data.
            quantity = int(item_data)
            subtotal = product.price * quantity

            total += subtotal
            product_count += quantity

            bag_items.append({
                "item_id": item_id,
                "quantity": quantity,
                "product": product,
                "extra_flowers": 0,
                "total_flowers":
                    product.included_flower_count,
                "customised_unit_price": product.price,
                "subtotal": subtotal,
            })

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
            free_delivery_threshold - total
        )
    else:
        delivery = Decimal("0.00")
        free_delivery_delta = Decimal("0.00")

    grand_total = delivery + total

    context = {
        "bag_items": bag_items,
        "total": total,
        "product_count": product_count,
        "delivery": delivery,
        "free_delivery_delta": free_delivery_delta,
        "free_delivery_threshold":
            free_delivery_threshold,
        "grand_total": grand_total,
    }

    return context
