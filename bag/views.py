from django.contrib import messages
from django.shortcuts import (
    HttpResponse,
    get_object_or_404,
    redirect,
    render,
    reverse,
)

from products.models import Product


MAX_GREETING_MESSAGE_LENGTH = 250


def view_bag(request):
    """Render the bag contents page."""

    return render(request, "bag/bag.html")


def _get_line_quantity(line_data):
    """
    Return the quantity from a bag line.

    This also supports older session data where the line value
    was stored directly as an integer.
    """

    if isinstance(line_data, dict):
        return line_data.get("quantity", 0)

    return line_data


def _create_line_data(quantity, greeting_message=""):
    """Create the dictionary stored for one customised bag line."""

    return {
        "quantity": quantity,
        "greeting_message": greeting_message,
    }


def add_to_bag(request, item_id):
    """Add a product and its customisation to the shopping bag."""

    product = get_object_or_404(Product, pk=item_id)

    try:
        quantity = int(request.POST.get("quantity", 1))
        extra_flowers = int(
            request.POST.get("extra_flowers", 0)
        )
    except (TypeError, ValueError):
        messages.error(
            request,
            "Invalid quantity selected.",
        )
        return redirect(
            "product_detail",
            product_id=item_id,
        )

    quantity = max(1, quantity)

    extra_flowers = max(
        0,
        min(extra_flowers, product.max_extra_flowers),
    )

    greeting_message = request.POST.get(
        "greeting_message",
        "",
    ).strip()

    if len(greeting_message) > MAX_GREETING_MESSAGE_LENGTH:
        messages.error(
            request,
            (
                "The greeting card message cannot exceed "
                f"{MAX_GREETING_MESSAGE_LENGTH} characters."
            ),
        )
        return redirect(
            "product_detail",
            product_id=item_id,
        )

    if not product.allows_greeting_message:
        greeting_message = ""

    redirect_url = request.POST.get(
        "redirect_url",
        reverse(
            "product_detail",
            args=[item_id],
        ),
    )

    size = request.POST.get("product_size")
    bag = request.session.get("bag", {})

    item_key = str(item_id)
    customisation_key = str(extra_flowers)

    if size:
        if item_key not in bag:
            bag[item_key] = {
                "items_by_size": {},
            }

        items_by_size = bag[item_key].setdefault(
            "items_by_size",
            {},
        )

        if size not in items_by_size:
            items_by_size[size] = {}

        size_items = items_by_size[size]

        if customisation_key in size_items:
            existing_line = size_items[customisation_key]

            existing_quantity = _get_line_quantity(
                existing_line
            )

            updated_quantity = (
                existing_quantity + quantity
            )

            size_items[customisation_key] = (
                _create_line_data(
                    updated_quantity,
                    greeting_message,
                )
            )

            messages.success(
                request,
                (
                    f"Updated size {size.upper()} "
                    f"{product.name} quantity to "
                    f"{updated_quantity}"
                ),
            )
        else:
            size_items[customisation_key] = (
                _create_line_data(
                    quantity,
                    greeting_message,
                )
            )

            if product.allows_greeting_message:
                success_message = (
                    f"Added size {size.upper()} "
                    f"{product.name} to your bag"
                )
            else:
                success_message = (
                    f"Added size {size.upper()} "
                    f"{product.name} with "
                    f"{extra_flowers} additional flowers "
                    "to your bag"
                )

            messages.success(
                request,
                success_message,
            )

    else:
        if item_key not in bag:
            bag[item_key] = {
                "items_by_customisation": {},
            }

        customisations = bag[item_key].setdefault(
            "items_by_customisation",
            {},
        )

        if customisation_key in customisations:
            existing_line = customisations[
                customisation_key
            ]

            existing_quantity = _get_line_quantity(
                existing_line
            )

            updated_quantity = (
                existing_quantity + quantity
            )

            customisations[customisation_key] = (
                _create_line_data(
                    updated_quantity,
                    greeting_message,
                )
            )

            messages.success(
                request,
                (
                    f"Updated {product.name} quantity to "
                    f"{updated_quantity}"
                ),
            )
        else:
            customisations[customisation_key] = (
                _create_line_data(
                    quantity,
                    greeting_message,
                )
            )

            if product.allows_greeting_message:
                success_message = (
                    f"Added {product.name} to your bag"
                )
            else:
                success_message = (
                    f"Added {product.name} with "
                    f"{extra_flowers} additional flowers "
                    "to your bag"
                )

            messages.success(
                request,
                success_message,
            )

    request.session["bag"] = bag
    request.session.modified = True

    return redirect(redirect_url)


def adjust_bag(request, item_id):
    """Adjust the quantity of a customised bag item."""

    product = get_object_or_404(Product, pk=item_id)

    try:
        quantity = int(
            request.POST.get("quantity", 1)
        )
        extra_flowers = int(
            request.POST.get("extra_flowers", 0)
        )
    except (TypeError, ValueError):
        messages.error(
            request,
            "Invalid quantity selected.",
        )
        return redirect(
            reverse("view_bag")
        )

    size = request.POST.get("product_size")
    bag = request.session.get("bag", {})

    item_key = str(item_id)
    customisation_key = str(extra_flowers)

    if item_key not in bag:
        messages.error(
            request,
            "This item is not in your bag.",
        )
        return redirect(
            reverse("view_bag")
        )

    if size:
        size_items = (
            bag[item_key]
            .get("items_by_size", {})
            .get(size, {})
        )

        if customisation_key not in size_items:
            messages.error(
                request,
                "This customised item is not in your bag.",
            )
            return redirect(
                reverse("view_bag")
            )

        existing_line = size_items[
            customisation_key
        ]

        if isinstance(existing_line, dict):
            greeting_message = existing_line.get(
                "greeting_message",
                "",
            )
        else:
            greeting_message = ""

        if quantity > 0:
            size_items[customisation_key] = (
                _create_line_data(
                    quantity,
                    greeting_message,
                )
            )

            messages.success(
                request,
                (
                    f"Updated size {size.upper()} "
                    f"{product.name} quantity to "
                    f"{quantity}"
                ),
            )
        else:
            size_items.pop(
                customisation_key,
                None,
            )

            if not size_items:
                bag[item_key][
                    "items_by_size"
                ].pop(
                    size,
                    None,
                )

            if not bag[item_key].get(
                "items_by_size"
            ):
                bag.pop(
                    item_key,
                    None,
                )

            messages.success(
                request,
                (
                    f"Removed size {size.upper()} "
                    f"{product.name} from your bag"
                ),
            )

    else:
        customisations = bag[item_key].get(
            "items_by_customisation",
            {},
        )

        if customisation_key not in customisations:
            messages.error(
                request,
                "This customised item is not in your bag.",
            )
            return redirect(
                reverse("view_bag")
            )

        existing_line = customisations[
            customisation_key
        ]

        if isinstance(existing_line, dict):
            greeting_message = existing_line.get(
                "greeting_message",
                "",
            )
        else:
            greeting_message = ""

        if quantity > 0:
            customisations[customisation_key] = (
                _create_line_data(
                    quantity,
                    greeting_message,
                )
            )

            messages.success(
                request,
                (
                    f"Updated {product.name} quantity "
                    f"to {quantity}"
                ),
            )
        else:
            customisations.pop(
                customisation_key,
                None,
            )

            if not customisations:
                bag.pop(
                    item_key,
                    None,
                )

            messages.success(
                request,
                f"Removed {product.name} from your bag",
            )

    request.session["bag"] = bag
    request.session.modified = True

    return redirect(
        reverse("view_bag")
    )


def remove_from_bag(request, item_id):
    """Remove one customised product line from the bag."""

    product = get_object_or_404(
        Product,
        pk=item_id,
    )

    try:
        extra_flowers = int(
            request.POST.get("extra_flowers", 0)
        )
    except (TypeError, ValueError):
        extra_flowers = 0

    size = request.POST.get("product_size")
    bag = request.session.get("bag", {})

    item_key = str(item_id)
    customisation_key = str(extra_flowers)

    try:
        if size:
            size_items = (
                bag[item_key]
                .get("items_by_size", {})
                .get(size, {})
            )

            size_items.pop(
                customisation_key,
                None,
            )

            if not size_items:
                bag[item_key][
                    "items_by_size"
                ].pop(
                    size,
                    None,
                )

            if not bag[item_key].get(
                "items_by_size"
            ):
                bag.pop(
                    item_key,
                    None,
                )

            messages.success(
                request,
                (
                    f"Removed size {size.upper()} "
                    f"{product.name} from your bag"
                ),
            )

        else:
            customisations = bag[item_key].get(
                "items_by_customisation",
                {},
            )

            customisations.pop(
                customisation_key,
                None,
            )

            if not customisations:
                bag.pop(
                    item_key,
                    None,
                )

            messages.success(
                request,
                f"Removed {product.name} from your bag",
            )

        request.session["bag"] = bag
        request.session.modified = True

        return HttpResponse(status=200)

    except (KeyError, TypeError) as error:
        messages.error(
            request,
            f"Error removing item: {error}",
        )

        return HttpResponse(status=500)
