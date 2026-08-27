from django.core.management.base import BaseCommand
from django.utils import timezone

from checkout.models import Order


class Command(BaseCommand):
    help = "Mark orders as completed after their delivery date has passed."

    def handle(self, *args, **options):
        today = timezone.localdate()

        updated = Order.objects.filter(
            delivery_date__lt=today
        ).exclude(
            status__in=["completed", "cancelled"]
        ).update(
            status="completed"
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"{updated} expired order(s) marked as completed."
            )
        )
