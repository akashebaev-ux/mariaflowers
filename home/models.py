from django.db import models


class ContactMessage(models.Model):
    """Store customer contact enquiries."""

    SUBJECT_CHOICES = [
        ("order", "Order enquiry"),
        ("delivery", "Delivery enquiry"),
        ("bouquet", "Bouquet enquiry"),
        ("payment", "Payment enquiry"),
        ("complaint", "Problem with an order"),
        ("other", "Other"),
    ]

    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    subject = models.CharField(
        max_length=20,
        choices=SUBJECT_CHOICES,
    )
    order_reference = models.CharField(
        max_length=100,
        blank=True,
    )
    message = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    email_sent = models.BooleanField(default=False)
    whatsapp_sent = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.get_subject_display()}"
