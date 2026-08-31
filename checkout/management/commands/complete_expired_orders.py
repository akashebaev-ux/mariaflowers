from django.core.management.base import BaseCommand

from checkout.utils import complete_expired_orders


class Command(BaseCommand):
    help = "Mark orders as completed after their delivery date has passed."

    def handle(self, *args, **options):
        updated = complete_expired_orders()

        self.stdout.write(
            self.style.SUCCESS(
                f"{updated} expired order(s) marked as completed."
            )
        )
