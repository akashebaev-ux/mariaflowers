import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models
from django.db.models import Sum

from django_countries.fields import CountryField

from products.models import Product
from profiles.models import UserProfile


DELIVERY_TIME_CHOICES = [
    ("09:00-11:00", "09:00-11:00"),
    ("11:00-13:00", "11:00-13:00"),
    ("13:00-15:00", "13:00-15:00"),
    ("15:00-17:00", "15:00-17:00"),
    ("17:00-19:00", "17:00-19:00"),
    ("19:00-21:00", "19:00-21:00"),
]


ORDER_STATUS_PENDING = "pending"
ORDER_STATUS_PREPARING = "preparing"
ORDER_STATUS_OUT_FOR_DELIVERY = "out_for_delivery"
ORDER_STATUS_COMPLETED = "completed"
ORDER_STATUS_CANCELLED = "cancelled"


ORDER_STATUS_CHOICES = [
    (
        ORDER_STATUS_PENDING,
        "Pending",
    ),
    (
        ORDER_STATUS_PREPARING,
        "Preparing",
    ),
    (
        ORDER_STATUS_OUT_FOR_DELIVERY,
        "Out for delivery",
    ),
    (
        ORDER_STATUS_COMPLETED,
        "Completed",
    ),
    (
        ORDER_STATUS_CANCELLED,
        "Cancelled",
    ),
]


class Order(models.Model):
    order_number = models.CharField(
        max_length=32,
        null=False,
        editable=False,
    )
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    full_name = models.CharField(
        max_length=50,
        null=False,
        blank=False,
    )
    email = models.EmailField(
        max_length=254,
        null=False,
        blank=False,
    )
    phone_number = models.CharField(
        max_length=20,
        null=False,
        blank=False,
    )
    country = CountryField(
        blank_label="Country *",
        null=False,
        blank=False,
    )
    postcode = models.CharField(
        max_length=20,
        null=True,
        blank=True,
    )
    town_or_city = models.CharField(
        max_length=40,
        null=False,
        blank=False,
    )
    street_address1 = models.CharField(
        max_length=80,
        null=False,
        blank=False,
    )
    street_address2 = models.CharField(
        max_length=80,
        null=True,
        blank=True,
    )
    county = models.CharField(
        max_length=80,
        null=True,
        blank=True,
    )
    delivery_date = models.DateField(
        null=True,
        blank=True,
    )
    delivery_time = models.CharField(
        max_length=20,
        choices=DELIVERY_TIME_CHOICES,
        null=True,
        blank=True,
    )
    date = models.DateTimeField(
        auto_now_add=True,
    )
    delivery_cost = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=False,
        default=0,
    )
    order_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=False,
        default=0,
    )
    grand_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=False,
        default=0,
    )
    original_bag = models.TextField(
        null=False,
        blank=False,
        default="",
    )
    stripe_pid = models.CharField(
        max_length=254,
        null=False,
        blank=False,
        default="",
    )
    is_paid = models.BooleanField(
        default=False,
    )
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=30,
        choices=ORDER_STATUS_CHOICES,
        default=ORDER_STATUS_PENDING,
    )

    @property
    def is_completed(self):
        """
        Return True when the order has been completed.
        """
        return self.status == ORDER_STATUS_COMPLETED

    @property
    def can_be_reviewed(self):
        """
        Return True when the order is completed and
        does not already have a review.
        """
        return (
            self.is_completed
            and not hasattr(self, "review")
        )

    def _generate_order_number(self):
        """
        Generate a random, unique order number using UUID.
        """
        return uuid.uuid4().hex.upper()

    def update_total(self):
        """
        Update grand total each time a line item is added,
        accounting for delivery costs.
        """
        self.order_total = (
            self.lineitems.aggregate(
                Sum("lineitem_total")
            )["lineitem_total__sum"]
            or 0
        )

        if self.order_total < settings.FREE_DELIVERY_THRESHOLD:
            self.delivery_cost = (
                self.order_total
                * settings.STANDARD_DELIVERY_PERCENTAGE
                / 100
            )
        else:
            self.delivery_cost = 0

        self.grand_total = (
            self.order_total
            + self.delivery_cost
        )

        self.save()

    def save(self, *args, **kwargs):
        """
        Set an order number if one has not been created.
        """
        if not self.order_number:
            self.order_number = (
                self._generate_order_number()
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return self.order_number


class OrderLineItem(models.Model):
    order = models.ForeignKey(
        Order,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="lineitems",
    )
    product = models.ForeignKey(
        Product,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
    )
    extra_flowers = models.PositiveIntegerField(
        default=0,
    )
    quantity = models.IntegerField(
        null=False,
        blank=False,
        default=0,
    )
    greeting_message = models.CharField(
        max_length=250,
        blank=True,
        help_text=(
            "Optional personalised greeting-card message"
        ),
    )
    lineitem_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=False,
        blank=False,
        editable=False,
    )

    def save(self, *args, **kwargs):
        """
        Calculate the product total, including extra flowers.
        """
        extra_flower_price = (
            self.product.extra_flower_price
            or 0
        )

        base_total = (
            self.product.price
            * self.quantity
        )

        extra_flowers_total = (
            extra_flower_price
            * self.extra_flowers
            * self.quantity
        )

        self.lineitem_total = (
            base_total
            + extra_flowers_total
        )

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"SKU {self.product.sku} on order "
            f"{self.order.order_number}"
        )


class Review(models.Model):
    """
    Store one customer review for a completed order.
    """

    order = models.OneToOneField(
        OrderLineItem,
        on_delete=models.CASCADE,
        related_name="review",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
    )
    comment = models.TextField(
        max_length=1000,
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        """
        Prevent reviews for orders that are not completed.
        """
        super().clean()

        if (
            self.order_line_item_id
            and self.order_line_item.order.status
            != ORDER_STATUS_COMPLETED
        ):
            raise ValidationError(
                {
                    "order_line_item": (
                        "Only products from completed orders "
                        "can be reviewed."
                    )
                }
            )

    def save(self, *args, **kwargs):
        """
        Validate the review before saving it.
        """
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"Review for {self.order_line_item.product.name} "
            f"- {self.rating}/5"
        )


class ReviewImage(models.Model):
    """
    Store a customer-uploaded image for a review.
    """

    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(
        upload_to="review_images/",
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["uploaded_at"]

    def __str__(self):
        return (
            f"Image for review "
            f"{self.review.pk}"
        )


class ReviewReaction(models.Model):
    """
    Record that a customer found a review helpful.
    """

    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name="reactions",
    )
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="review_reactions",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "review",
                    "user_profile",
                ],
                name="unique_review_reaction",
            ),
        ]

    def __str__(self):
        return (
            f"{self.user_profile} found "
            f"review {self.review.pk} helpful"
        )


class WhatsAppMessage(models.Model):
    """
    Store WhatsApp notification attempts for an order.
    """

    STATUS_PENDING = "pending"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (
            STATUS_PENDING,
            "Pending",
        ),
        (
            STATUS_SENT,
            "Sent",
        ),
        (
            STATUS_FAILED,
            "Failed",
        ),
    ]

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="whatsapp_messages",
    )
    recipient = models.CharField(
        max_length=30,
    )
    message_body = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    provider_message_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    error_message = models.TextField(
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"WhatsApp message for "
            f"{self.order.order_number}: "
            f"{self.status}"
        )
