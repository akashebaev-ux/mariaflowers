from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Avg


class Category(models.Model):

    class Meta:
        verbose_name_plural = "Categories"

    name = models.CharField(max_length=254)
    friendly_name = models.CharField(
        max_length=254,
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.name

    def get_friendly_name(self):
        return self.friendly_name


class Product(models.Model):
    category = models.ForeignKey(
        "Category",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    sku = models.CharField(
        max_length=254,
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=254)
    description = models.TextField()

    has_sizes = models.BooleanField(
        default=False,
        null=True,
        blank=True,
    )

    allows_greeting_message = models.BooleanField(
        default=False,
        help_text=(
            "Allow customers to add a personalised message "
            "to this product"
        ),
    )

    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
    )

    rating = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )

    image_url = models.URLField(
        max_length=1024,
        null=True,
        blank=True,
    )

    image = models.ImageField(
        null=True,
        blank=True,
    )

    included_flower_count = models.PositiveIntegerField(
        default=25,
        help_text="Number of flowers included in the bouquet",
    )

    extra_flower_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Price for each additional flower",
    )

    max_extra_flowers = models.PositiveIntegerField(
        default=300,
        help_text="Maximum number of additional flowers",
    )

    @property
    def average_rating(self):
        """
        Return the average customer review rating
        for this product.
        """
        result = self.orderlineitem_set.filter(
            review__isnull=False,
        ).aggregate(
            average=Avg("review__rating")
        )

        return result["average"]

    @property
    def maximum_flower_count(self):
        return (
            self.included_flower_count
            + self.max_extra_flowers
        )

    def __str__(self):
        return self.name
