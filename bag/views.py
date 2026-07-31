from django.contrib import messages
from django.shortcuts import (
    HttpResponse,
    get_object_or_404,
    redirect,
    render,
    reverse,
)

from products.models import Product


def view_bag(request):
    """Render the bag contents page."""

    return render(request, "bag/bag.html")


def add_to_bag(request, item_id):
    """Add a product and its customisation to the shopping bag."""

    product = get_object_or_404(Product, pk=item_id)

    try:
        quantity = int(request.POST.get("quantity", 1))
        extra_flowers = int(
            request.POST.get("extra_flowers", 0)
        )
    except (TypeError, ValueError):
        messages.error(request, "Invalid quantity selected.")
        return redirect("product_detail", product_id=item_id)

    quantity = max(1, quantity)

    extra_flowers = max(
        0,
        min(extra_flowers, product.max_extra_flowers),
    )

    redirect_url = request.POST.get(
        "redirect_url",
        reverse("product_detail", args=[item_id]),
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

        if size not in bag[item_key]["items_by_size"]:
            bag[item_key]["items_by_size"][size] = {}

        size_items = bag[item_key]["items_by_size"][size]

        if customisation_key in size_items:
            size_items[customisation_key] += quantity

            messages.success(
                request,
                (
                    f"Updated size {size.upper()} "
                    f"{product.name} quantity to "
                    f"{size_items[customisation_key]}"
                ),
            )
        else:
            size_items[customisation_key] = quantity

            messages.success(
                request,
                (
                    f"Added size {size.upper()} "
                    f"{product.name} with "
                    f"{extra_flowers} additional flowers "
                    "to your bag"
                ),
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
            customisations[customisation_key] += quantity

            messages.success(
                request,
                (
                    f"Updated {product.name} quantity to "
                    f"{customisations[customisation_key]}"
                ),
            )
        else:
            customisations[customisation_key] = quantity

            messages.success(
                request,
                (
                    f"Added {product.name} with "
                    f"{extra_flowers} additional flowers "
                    "to your bag"
                ),
            )

    request.session["bag"] = bag

    return redirect(redirect_url)


def adjust_bag(request, item_id):
    """Adjust the quantity of a customised bag item."""

    product = get_object_or_404(Product, pk=item_id)

    try:
        quantity = int(request.POST.get("quantity", 1))
        extra_flowers = int(
            request.POST.get("extra_flowers", 0)
        )
    except (TypeError, ValueError):
        messages.error(request, "Invalid quantity selected.")
        return redirect(reverse("view_bag"))

    size = request.POST.get("product_size")
    bag = request.session.get("bag", {})

    item_key = str(item_id)
    customisation_key = str(extra_flowers)

    if item_key not in bag:
        messages.error(request, "This item is not in your bag.")
        return redirect(reverse("view_bag"))

    if size:
        size_items = (
            bag[item_key]
            .get("items_by_size", {})
            .get(size, {})
        )

        if quantity > 0:
            size_items[customisation_key] = quantity

            messages.success(
                request,
                (
                    f"Updated size {size.upper()} "
                    f"{product.name} quantity to {quantity}"
                ),
            )
        else:
            size_items.pop(customisation_key, None)

            if not size_items:
                bag[item_key]["items_by_size"].pop(
                    size,
                    None,
                )

            if not bag[item_key]["items_by_size"]:
                bag.pop(item_key, None)

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

        if quantity > 0:
            customisations[customisation_key] = quantity

            messages.success(
                request,
                (
                    f"Updated {product.name} quantity "
                    f"to {quantity}"
                ),
            )
        else:
            customisations.pop(customisation_key, None)

            if not customisations:
                bag.pop(item_key, None)

            messages.success(
                request,
                f"Removed {product.name} from your bag",
            )

    request.session["bag"] = bag

    return redirect(reverse("view_bag"))


def remove_from_bag(request, item_id):
    """Remove one customised product line from the shopping bag."""

    product = get_object_or_404(Product, pk=item_id)

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

            size_items.pop(customisation_key, None)

            if not size_items:
                bag[item_key]["items_by_size"].pop(
                    size,
                    None,
                )

            if not bag[item_key]["items_by_size"]:
                bag.pop(item_key, None)

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

            customisations.pop(customisation_key, None)

            if not customisations:
                bag.pop(item_key, None)

            messages.success(
                request,
                f"Removed {product.name} from your bag",
            )

        request.session["bag"] = bag

        return HttpResponse(status=200)

    except (KeyError, TypeError) as error:
        messages.error(
            request,
            f"Error removing item: {error}",
        )
        return HttpResponse(status=500)
