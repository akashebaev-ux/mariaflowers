from django.utils import timezone

from checkout.models import Order


def complete_expired_orders(profile=None):
    """
    Mark expired orders as completed.

    If a profile is provided, only update that user's orders.
    Otherwise, update all expired orders.
    """
    today = timezone.localdate()

    orders = Order.objects.filter(
        delivery_date__lt=today
    ).exclude(
        status__in=["completed", "cancelled"]
    )

    if profile is not None:
        orders = orders.filter(user_profile=profile)

    return orders.update(status="completed")
