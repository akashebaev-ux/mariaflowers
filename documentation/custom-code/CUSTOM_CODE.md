# Maria Flowers Custom Code

> [!NOTE]  
> Return back to the [README.md](README.md) file.

Maria Flowers was developed using the Code Institute **Boutique Ado** walkthrough project as its initial foundation.

The original Boutique Ado project provided standard e-commerce functionality such as product management, a shopping bag, checkout, Stripe payments, and customer profiles.

I substantially adapted and extended this foundation to create Maria Flowers as a flower-delivery e-commerce application.

This document highlights the main models, fields, business logic, and integrations that were added or significantly modified beyond the original Boutique Ado project.

---

## Custom Models

The following Django models were added specifically for Maria Flowers:

- `Review`
- `ReviewImage`
- `ReviewReaction`
- `WhatsAppMessage`
- `ContactMessage`
- `NewsletterSubscriber`

### Review

The `Review` model allows customers to leave ratings and comments for products they have purchased.

```python
class Review(models.Model):
    order_line_item = models.OneToOneField(
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
```

Additional validation ensures that products can only be reviewed after the associated order has been completed.

The full implementation can be found in:

[`checkout/models.py`](../../checkout/models.py)

---

### ReviewImage

The `ReviewImage` model allows images to be associated with customer reviews.

```python
class ReviewImage(models.Model):
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
```

The full implementation can be found in:

[`checkout/models.py`](../../checkout/models.py)

---

### ReviewReaction

The `ReviewReaction` model allows authenticated customers to mark reviews as helpful.

```python
class ReviewReaction(models.Model):
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
```

A database uniqueness constraint prevents the same customer from reacting to the same review more than once.

The full implementation can be found in:

[`checkout/models.py`](../../checkout/models.py)

---

### WhatsAppMessage

The `WhatsAppMessage` model stores WhatsApp order-notification attempts.

```python
class WhatsAppMessage(models.Model):
    STATUS_PENDING = "pending"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SENT, "Sent"),
        (STATUS_FAILED, "Failed"),
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
```

This allows Maria Flowers to keep a record of whether a WhatsApp notification was successfully sent or failed.

The full implementation can be found in:

[`checkout/models.py`](../../checkout/models.py)

---

### ContactMessage

The `ContactMessage` model stores enquiries submitted through the Maria Flowers contact form.

```python
class ContactMessage(models.Model):
    name = models.CharField(...)
    email = models.EmailField(...)
    phone = models.CharField(..., blank=True)
    subject = models.CharField(...)
    order_reference = models.CharField(..., blank=True)
    message = models.TextField(...)
```

This means contact enquiries remain stored in the database even when email or WhatsApp notifications are also sent.

The full implementation can be found in:

[`home/models.py`](../../home/models.py)

---

### NewsletterSubscriber

The newsletter feature uses a custom model to store subscriber email addresses.

```python
class NewsletterSubscriber(models.Model):
    email = models.EmailField(
        unique=True,
    )

    subscribed_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return self.email
```

The unique email field prevents duplicate newsletter subscriptions.

---

## Extended Boutique Ado Models

Some original Boutique Ado models were retained but significantly extended for Maria Flowers.

These include:

- `Product`
- `Order`
- `OrderLineItem`

---

## Product Extensions

The original `Product` model was adapted for flower products and bouquet customisation.

Maria Flowers product data includes flower-specific fields such as:

```python
included_flower_count = models.PositiveIntegerField(...)
extra_flower_price = models.DecimalField(...)
max_extra_flowers = models.PositiveIntegerField(...)
```

These additions allow customers to customise selected flower arrangements by increasing the number of flowers.

The full implementation can be found in:

[`products/models.py`](../../products/models.py)

---

## Order Extensions

The original Boutique Ado `Order` model was extended to support flower delivery and order tracking.

### Delivery Date

```python
delivery_date = models.DateField(
    null=True,
    blank=True,
)
```

Customers can select the date on which the flowers should be delivered.

### Delivery Time

```python
delivery_time = models.CharField(
    max_length=20,
    choices=DELIVERY_TIME_CHOICES,
    null=True,
    blank=True,
)
```

Maria Flowers provides defined delivery windows:

- 09:00–11:00
- 11:00–13:00
- 13:00–15:00
- 15:00–17:00
- 17:00–19:00
- 19:00–21:00

### Payment Status

```python
is_paid = models.BooleanField(
    default=False,
)

paid_at = models.DateTimeField(
    null=True,
    blank=True,
)
```

These fields allow the application to distinguish successfully paid orders before triggering functionality such as WhatsApp notifications.

### Order Status

```python
status = models.CharField(
    max_length=30,
    choices=ORDER_STATUS_CHOICES,
    default=ORDER_STATUS_PENDING,
)
```

This supports the order lifecycle and allows customers and administrators to track the status of an order.

---

## Automatic Order Completion

Maria Flowers includes custom logic to automatically mark orders as completed once their delivery date has passed.

```python
def complete_expired_orders(profile=None):
    today = timezone.localdate()

    orders = Order.objects.filter(
        delivery_date__lt=today
    ).exclude(
        status__in=["completed", "cancelled"]
    )

    if profile is not None:
        orders = orders.filter(
            user_profile=profile
        )

    return orders.update(
        status="completed"
    )
```

The full implementation can be found in:

[`checkout/utils.py`](../../checkout/utils.py)

---

## Order Line Item Extensions

The Boutique Ado `OrderLineItem` model was extended to support flower customisation.

### Extra Flowers

```python
extra_flowers = models.PositiveIntegerField(
    default=0,
)
```

Customers can increase the number of flowers included in selected bouquets.

### Greeting Card Message

```python
greeting_message = models.CharField(
    max_length=250,
    blank=True,
    help_text=(
        "Optional personalised greeting-card message"
    ),
)
```

Customers can include a personalised message with their flower order.

### Custom Line Item Calculation

The line-item calculation was modified to account for additional flowers.

```python
def save(self, *args, **kwargs):
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
```

---

## Verified Review System

Maria Flowers includes a custom review system tied to actual purchases.

The application checks that:

- The customer is authenticated.
- The product belongs to an eligible customer order.
- The associated order is completed.
- The rating is between 1 and 5.
- Duplicate reviews for the same purchased item are prevented.
- Review images can be uploaded.
- Authenticated customers can mark reviews as helpful.
- Duplicate helpful reactions are prevented.

This functionality was developed specifically for Maria Flowers and was not part of the original Boutique Ado walkthrough.

---

## WhatsApp Business Integration

Maria Flowers integrates with the **WhatsApp Business Cloud API**.

Custom functionality includes:

- Sending paid-order notifications.
- Creating message content from order information.
- Formatting telephone numbers.
- Recording WhatsApp messages in the database.
- Recording whether messages are pending, sent, or failed.
- Storing provider message IDs.
- Recording API error messages.
- Preventing duplicate paid-order notifications.
- Sending contact-form notifications.
- Supporting Meta webhook verification.

Sensitive API credentials are stored in environment variables rather than directly in the source code.

### Duplicate WhatsApp Prevention

Before sending a paid-order notification, the application checks whether a successful message already exists for that order.

```python
previous_sent_message = order.whatsapp_messages.filter(
    status=WhatsAppMessage.STATUS_SENT,
).exists()

if previous_sent_message:
    return None
```

This prevents duplicate order notifications.

---

## Contact Functionality

A custom contact system was added to Maria Flowers.

Visitors can submit:

- Name
- Email
- Phone number
- Subject
- Order reference
- Message

The submitted enquiry is:

1. Validated using a Django form.
2. Stored in the database.
3. Sent by email.
4. Sent through the WhatsApp integration where configured.

---

## Newsletter Subscription

Maria Flowers includes a newsletter subscription form.

Visitors can enter their email address without creating an account.

Django validation checks the submitted email address, and successfully subscribed addresses are stored in the database.

The `unique=True` constraint prevents the same email address from being registered multiple times.

---

## Search and Filtering

The Boutique Ado product search functionality was adapted for the Maria Flowers product catalogue.

Customers can:

- Search for flowers.
- Browse flower categories.
- Sort products.
- Filter the product catalogue.
- Sort using product ratings.

This functionality was adapted to work with flower products rather than the original Boutique Ado catalogue.

---

## Order History Enhancements

Customer order history was extended to provide flower-delivery-specific information.

Customers can view information including:

- Order number.
- Delivery date.
- Delivery time.
- Order status.
- Products purchased.
- Review eligibility.

This connects the ordering, delivery, and review workflows.

---

## Django Admin Enhancements

The Django Admin interface was extended to manage Maria Flowers-specific data including:

- Flower products.
- Orders.
- Order statuses.
- Reviews.
- Review images.
- Review reactions.
- WhatsApp messages.
- Contact enquiries.
- Newsletter subscribers.

---

## Additional Front-End Development

Maria Flowers also contains substantial front-end changes beyond Boutique Ado.

These include:

- Maria Flowers branding.
- Flower-specific imagery.
- Flower product catalogue.
- Custom homepage.
- Contact page.
- About page.
- FAQ page.
- Privacy Policy.
- Terms and Conditions.
- Delivery Policy.
- Refund Policy.
- Responsive mobile layouts.
- Tablet layouts.
- Desktop layouts.
- Accessibility improvements.
- HTML validation fixes.
- CSS validation fixes.
- Lighthouse performance improvements.
- Custom error pages.

---

## Summary

The original Boutique Ado walkthrough was used as the initial e-commerce foundation, while Maria Flowers adds substantial custom functionality for flower ordering, bouquet customisation, delivery scheduling, order lifecycle management, verified customer reviews, WhatsApp communication, newsletter marketing, and customer contact management.

The production source code remains inside the appropriate Django applications. This document provides a central overview of the most important custom code and functionality developed beyond the original Boutique Ado project.