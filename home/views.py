from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.shortcuts import redirect, render

from .forms import ContactForm, NewsletterForm
from .whatsapp import send_contact_whatsapp
from .models import NewsletterSubscriber


def index(request):
    """A view to return the index page."""
    return render(request, "home/index.html")


def contact(request):
    """Display and process the customer contact form."""

    if request.method == "POST":
        form = ContactForm(request.POST)

        if form.is_valid():
            contact_message = form.save()

            email_subject = (
                "Maria Flowers Contact - "
                f"{contact_message.get_subject_display()}"
            )

            email_body = f"""
New customer enquiry from Maria Flowers

Name:
{contact_message.name}

Email:
{contact_message.email}

Phone:
{contact_message.phone or "Not provided"}

Subject:
{contact_message.get_subject_display()}

Order Reference:
{contact_message.order_reference or "Not provided"}

Message:
{contact_message.message}
"""

            try:
                send_mail(
                    subject=email_subject,
                    message=email_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.CONTACT_EMAIL],
                    fail_silently=False,
                )

                contact_message.email_sent = True
                contact_message.save(
                    update_fields=["email_sent"]
                )

            except Exception as error:
                print("EMAIL ERROR:", error)

            whatsapp_sent = send_contact_whatsapp(
                contact_message
            )

            if whatsapp_sent:
                contact_message.whatsapp_sent = True
                contact_message.save(
                    update_fields=["whatsapp_sent"]
                )

            messages.success(
                request,
                "Thank you. Your message has been received."
            )

            return redirect("contact")

    else:
        form = ContactForm()

    context = {
        "form": form,
    }

    return render(
        request,
        "home/contact.html",
        context,
    )


def newsletter_signup(request):
    """Handle newsletter subscriptions."""

    if request.method == "POST":
        form = NewsletterForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data["email"]

            if NewsletterSubscriber.objects.filter(email=email).exists():
                messages.info(
                    request,
                    "This email is already subscribed to our newsletter."
                )
            else:
                form.save()
                messages.success(
                    request,
                    "Thank you! You have successfully subscribed "
                    "to the Maria Flowers newsletter."
                )
        else:
            messages.error(
                request,
                "Please enter a valid email address."
            )

    return redirect(request.META.get("HTTP_REFERER", "/"))
