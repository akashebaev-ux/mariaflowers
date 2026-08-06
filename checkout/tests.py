from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from checkout.models import (
    ORDER_STATUS_COMPLETED,
    ORDER_STATUS_PREPARING,
    Order,
    OrderLineItem,
    Review,
    ReviewImage,
    ReviewReaction,
)
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


class ReviewModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="reviewcustomer",
            email="review@example.com",
            password="test-password-123",
        )

        self.profile = self.user.userprofile

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

    def test_rating_between_one_and_five_is_valid(self):
        review = Review.objects.create(
            order=self.order,
            rating=5,
        )

        self.assertEqual(review.rating, 5)

    def test_written_review_can_be_blank(self):
        review = Review.objects.create(
            order=self.order,
            rating=4,
            comment="",
        )

        self.assertEqual(review.comment, "")

    def test_written_review_is_saved(self):
        review = Review.objects.create(
            order=self.order,
            rating=5,
            comment="Beautiful flowers and excellent delivery.",
        )

        self.assertEqual(
            review.comment,
            "Beautiful flowers and excellent delivery.",
        )

    def test_rating_below_one_is_invalid(self):
        review = Review(
            order=self.order,
            rating=0,
        )

        with self.assertRaises(ValidationError):
            review.full_clean()

    def test_rating_above_five_is_invalid(self):
        review = Review(
            order=self.order,
            rating=6,
        )

        with self.assertRaises(ValidationError):
            review.full_clean()

    def test_incomplete_order_cannot_be_reviewed(self):
        self.order.status = ORDER_STATUS_PREPARING
        self.order.save()

        review = Review(
            order=self.order,
            rating=5,
        )

        with self.assertRaises(ValidationError):
            review.save()

    def test_only_one_review_can_be_submitted_per_order(self):
        Review.objects.create(
            order=self.order,
            rating=5,
        )

        with self.assertRaises(ValidationError):
            Review.objects.create(
                order=self.order,
                rating=4,
            )

    def test_completed_order_can_be_reviewed(self):
        self.assertTrue(self.order.is_completed)
        self.assertTrue(self.order.can_be_reviewed)

    def test_reviewed_order_cannot_be_reviewed_again(self):
        Review.objects.create(
            order=self.order,
            rating=5,
        )

        self.assertFalse(self.order.can_be_reviewed)


class ReviewImageModelTests(TestCase):
    def setUp(self):
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

        self.review = Review.objects.create(
            order=self.order,
            rating=5,
            comment="The bouquet looked wonderful.",
        )

    def test_review_image_is_connected_to_review(self):
        review_image = ReviewImage(
            review=self.review,
            image="review_images/test-bouquet.webp",
        )

        review_image.save()

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
    def setUp(self):
        self.user = User.objects.create_user(
            username="helpfulcustomer",
            email="helpful@example.com",
            password="test-password-123",
        )

        self.profile = self.user.userprofile

        self.order = Order.objects.create(
            full_name="Reaction Customer",
            email="reaction@example.com",
            phone_number="123456789",
            country="KZ",
            postcode="050000",
            town_or_city="Almaty",
            street_address1="Tole Bi Street 30",
            status=ORDER_STATUS_COMPLETED,
        )

        self.review = Review.objects.create(
            order=self.order,
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
