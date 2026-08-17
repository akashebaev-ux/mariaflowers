from django.contrib import messages
from django.shortcuts import render, redirect
from django.conf import settings
from django.core.mail import send_mail

from .forms import ContactForm


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

            except Exception:
                pass

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
        context
    )
