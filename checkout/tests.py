from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from checkout.models import (
    ORDER_STATUS_COMPLETED,
    ORDER_STATUS_PREPARING,
    Order,
    OrderLineItem,
    Review,
    ReviewImage,
    ReviewReaction,
)
from checkout.utils import complete_expired_orders
from products.models import Product


class GreetingCardOrderTests(TestCase):
    """Tests for greeting card messages on order line items."""

    def setUp(self):
        self.card = Product.objects.create(
            name="Happy Birthday Card",
            price=Decimal("4.50"),
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

        self.assertEqual(
            line_item.greeting_message,
            "",
        )

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

        self.assertEqual(
            field.max_length,
            250,
        )


class ReviewModelTests(TestCase):
    """Tests for customer product reviews."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="reviewcustomer",
            email="review@example.com",
            password="test-password-123",
        )

        self.profile = self.user.userprofile

        self.product = Product.objects.create(
            name="Review Bouquet",
            price=Decimal("35.00"),
        )

        self.order = Order.objects.create(
            user_profile=self.profile,
            full_name="Review Customer",
            email="review@example.com",
            phone_number="123456789",
            country="KZ",
            postcode="050000",
            town_or_city="Almaty",
            street_address1="Dostyk Avenue 10",
            status=ORDER_STATUS_COMPLETED,
        )

        self.line_item = OrderLineItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
        )

    def test_rating_between_one_and_five_is_valid(self):
        review = Review.objects.create(
            order_line_item=self.line_item,
            rating=5,
        )

        self.assertEqual(
            review.rating,
            5,
        )

    def test_written_review_can_be_blank(self):
        review = Review.objects.create(
            order_line_item=self.line_item,
            rating=4,
            comment="",
        )

        self.assertEqual(
            review.comment,
            "",
        )

    def test_written_review_is_saved(self):
        review = Review.objects.create(
            order_line_item=self.line_item,
            rating=5,
            comment="Beautiful flowers and excellent delivery.",
        )

        self.assertEqual(
            review.comment,
            "Beautiful flowers and excellent delivery.",
        )

    def test_rating_below_one_is_invalid(self):
        review = Review(
            order_line_item=self.line_item,
            rating=0,
        )

        with self.assertRaises(ValidationError):
            review.full_clean()

    def test_rating_above_five_is_invalid(self):
        review = Review(
            order_line_item=self.line_item,
            rating=6,
        )

        with self.assertRaises(ValidationError):
            review.full_clean()

    def test_incomplete_order_cannot_be_reviewed(self):
        self.order.status = ORDER_STATUS_PREPARING
        self.order.save()

        review = Review(
            order_line_item=self.line_item,
            rating=5,
        )

        with self.assertRaises(ValidationError):
            review.save()

    def test_only_one_review_can_be_submitted_per_line_item(self):
        Review.objects.create(
            order_line_item=self.line_item,
            rating=5,
        )

        second_review = Review(
            order_line_item=self.line_item,
            rating=4,
        )

        with self.assertRaises(ValidationError):
            second_review.full_clean()

    def test_completed_order_line_item_can_be_reviewed(self):
        self.assertEqual(
            self.line_item.order.status,
            ORDER_STATUS_COMPLETED,
        )

        review = Review.objects.create(
            order_line_item=self.line_item,
            rating=5,
        )

        self.assertEqual(
            review.order_line_item,
            self.line_item,
        )

    def test_review_is_connected_to_correct_product(self):
        review = Review.objects.create(
            order_line_item=self.line_item,
            rating=5,
        )

        self.assertEqual(
            review.order_line_item.product,
            self.product,
        )


class ReviewImageModelTests(TestCase):
    """Tests for images uploaded with reviews."""

    def setUp(self):
        self.product = Product.objects.create(
            name="Image Test Bouquet",
            price=Decimal("40.00"),
        )

        self.order = Order.objects.create(
            full_name="Image Customer",
            email="image@example.com",
            phone_number="123456789",
            country="KZ",
            postcode="050000",
            town_or_city="Almaty",
            street_address1="Satpaev Street 20",
            status=ORDER_STATUS_COMPLETED,
        )

        self.line_item = OrderLineItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
        )

        self.review = Review.objects.create(
            order_line_item=self.line_item,
            rating=5,
            comment="The bouquet looked wonderful.",
        )

    def test_review_image_is_connected_to_review(self):
        review_image = ReviewImage.objects.create(
            review=self.review,
            image="review_images/test-bouquet.webp",
        )

        self.assertEqual(
            review_image.review,
            self.review,
        )

    def test_review_can_have_multiple_images(self):
        ReviewImage.objects.create(
            review=self.review,
            image="review_images/first.webp",
        )

        ReviewImage.objects.create(
            review=self.review,
            image="review_images/second.webp",
        )

        self.assertEqual(
            self.review.images.count(),
            2,
        )


class ReviewReactionModelTests(TestCase):
    """Tests for helpful reactions on customer reviews."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="helpfulcustomer",
            email="helpful@example.com",
            password="test-password-123",
        )

        self.profile = self.user.userprofile

        self.product = Product.objects.create(
            name="Reaction Test Bouquet",
            price=Decimal("45.00"),
        )

        self.order = Order.objects.create(
            user_profile=self.profile,
            full_name="Reaction Customer",
            email="reaction@example.com",
            phone_number="123456789",
            country="KZ",
            postcode="050000",
            town_or_city="Almaty",
            street_address1="Tole Bi Street 30",
            status=ORDER_STATUS_COMPLETED,
        )

        self.line_item = OrderLineItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
        )

        self.review = Review.objects.create(
            order_line_item=self.line_item,
            rating=5,
            comment="Very helpful review.",
        )

    def test_user_can_mark_review_as_helpful(self):
        reaction = ReviewReaction.objects.create(
            review=self.review,
            user_profile=self.profile,
        )

        self.assertEqual(
            reaction.review,
            self.review,
        )

        self.assertEqual(
            reaction.user_profile,
            self.profile,
        )

    def test_user_can_react_only_once_to_same_review(self):
        ReviewReaction.objects.create(
            review=self.review,
            user_profile=self.profile,
        )

        with self.assertRaises(IntegrityError):
            ReviewReaction.objects.create(
                review=self.review,
                user_profile=self.profile,
            )


class OrderTotalTests(TestCase):
    """Tests for order and line-item total calculations."""

    def setUp(self):
        self.product = Product.objects.create(
            name="Test Bouquet",
            price=Decimal("25.00"),
        )

        self.order = Order.objects.create(
            full_name="Total Test Customer",
            email="total@example.com",
            phone_number="123456789",
            country="KZ",
            postcode="050000",
            town_or_city="Almaty",
            street_address1="Abay Avenue 20",
        )

    def test_line_item_total_is_calculated_correctly(self):
        line_item = OrderLineItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
        )

        self.assertEqual(
            line_item.lineitem_total,
            Decimal("50.00"),
        )

    def test_order_total_updates_when_item_is_added(self):
        OrderLineItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.order_total,
            Decimal("50.00"),
        )

    def test_order_total_updates_when_quantity_changes(self):
        line_item = OrderLineItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
        )

        line_item.quantity = 3
        line_item.save()

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.order_total,
            Decimal("75.00"),
        )

    def test_order_total_updates_when_item_is_deleted(self):
        line_item = OrderLineItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
        )

        line_item.delete()

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.order_total,
            Decimal("0.00"),
        )


class ExpiredOrderCompletionTests(TestCase):
    """Tests for automatically completing expired orders."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="deliverycustomer",
            email="delivery@example.com",
            password="test-password-123",
        )

        self.profile = self.user.userprofile
        self.today = timezone.localdate()

    def create_order(
        self,
        delivery_date,
        status=ORDER_STATUS_PREPARING,
        profile=None,
        email="delivery@example.com",
    ):
        return Order.objects.create(
            user_profile=profile,
            full_name="Delivery Customer",
            email=email,
            phone_number="123456789",
            country="KZ",
            postcode="050000",
            town_or_city="Almaty",
            street_address1="Dostyk Avenue 20",
            delivery_date=delivery_date,
            status=status,
        )

    def test_expired_order_is_marked_completed(self):
        order = self.create_order(
            delivery_date=self.today - timedelta(days=1),
        )

        updated = complete_expired_orders()

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            ORDER_STATUS_COMPLETED,
        )

        self.assertEqual(
            updated,
            1,
        )

    def test_future_order_is_not_marked_completed(self):
        order = self.create_order(
            delivery_date=self.today + timedelta(days=1),
        )

        updated = complete_expired_orders()

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            ORDER_STATUS_PREPARING,
        )

        self.assertEqual(
            updated,
            0,
        )

    def test_order_for_today_is_not_marked_completed(self):
        order = self.create_order(
            delivery_date=self.today,
        )

        updated = complete_expired_orders()

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            ORDER_STATUS_PREPARING,
        )

        self.assertEqual(
            updated,
            0,
        )

    def test_cancelled_order_is_not_marked_completed(self):
        order = self.create_order(
            delivery_date=self.today - timedelta(days=1),
            status="cancelled",
        )

        updated = complete_expired_orders()

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            "cancelled",
        )

        self.assertEqual(
            updated,
            0,
        )

    def test_already_completed_order_remains_completed(self):
        order = self.create_order(
            delivery_date=self.today - timedelta(days=1),
            status=ORDER_STATUS_COMPLETED,
        )

        updated = complete_expired_orders()

        order.refresh_from_db()

        self.assertEqual(
            order.status,
            ORDER_STATUS_COMPLETED,
        )

        self.assertEqual(
            updated,
            0,
        )

    def test_only_profile_orders_are_completed_when_profile_given(self):
        second_user = User.objects.create_user(
            username="secondcustomer",
            email="second@example.com",
            password="test-password-123",
        )

        second_profile = second_user.userprofile

        first_order = self.create_order(
            delivery_date=self.today - timedelta(days=1),
            profile=self.profile,
            email="delivery@example.com",
        )

        second_order = self.create_order(
            delivery_date=self.today - timedelta(days=1),
            profile=second_profile,
            email="second@example.com",
        )

        updated = complete_expired_orders(
            profile=self.profile
        )

        first_order.refresh_from_db()
        second_order.refresh_from_db()

        self.assertEqual(
            first_order.status,
            ORDER_STATUS_COMPLETED,
        )

        self.assertEqual(
            second_order.status,
            ORDER_STATUS_PREPARING,
        )

        self.assertEqual(
            updated,
            1,
        )


class DeliveryDateTests(TestCase):
    """Tests for storing customer delivery dates."""

    def test_delivery_date_is_saved_correctly(self):
        delivery_date = (
            timezone.localdate() + timedelta(days=3)
        )

        order = Order.objects.create(
            full_name="Delivery Date Customer",
            email="date@example.com",
            phone_number="123456789",
            country="KZ",
            postcode="050000",
            town_or_city="Almaty",
            street_address1="Satpaev Street 10",
            delivery_date=delivery_date,
        )

        order.refresh_from_db()

        self.assertEqual(
            order.delivery_date,
            delivery_date,
        )
