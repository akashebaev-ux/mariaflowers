from django.test import TestCase

from checkout.models import Order, OrderLineItem
from products.models import Product


class GreetingCardOrderTests(TestCase):
    def setUp(self):
        self.card = Product.objects.create(
            name="Happy Birthday Card",
            price=4.50,
            allows_greeting_message=True,
        )

        self.order = Order.objects.create(
            full_name="Test Customer",
            email="customer@example.com",
            phone_number="123456789",
            country="KZ",
            postcode="050000",
            town_or_city="Almaty",
            street_address1="Abay Avenue 1",
        )

    def test_greeting_message_can_be_blank(self):
        line_item = OrderLineItem.objects.create(
            order=self.order,
            product=self.card,
            quantity=1,
        )

        self.assertEqual(line_item.greeting_message, "")

    def test_greeting_message_is_saved(self):
        line_item = OrderLineItem.objects.create(
            order=self.order,
            product=self.card,
            quantity=1,
            greeting_message="Happy Birthday, Mum!",
        )

        self.assertEqual(
            line_item.greeting_message,
            "Happy Birthday, Mum!",
        )

    def test_greeting_message_max_length_is_250(self):
        field = OrderLineItem._meta.get_field(
            "greeting_message"
        )

        self.assertEqual(field.max_length, 250)
