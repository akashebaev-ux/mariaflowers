from django import forms
from .models import ContactMessage
from .models import NewsletterSubscriber


class ContactForm(forms.ModelForm):
    """Form for customer enquiries."""

    class Meta:
        model = ContactMessage

        fields = [
            "name",
            "email",
            "phone",
            "subject",
            "order_reference",
            "message",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Your full name",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Your email address",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Your phone number",
                    "inputmode": "numeric",
                    "pattern": "[0-9]*",
                }
            ),
            "subject": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "order_reference": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Order number, if applicable",
                }
            ),
            "message": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 8,
                    "placeholder": "How can we help you?",
                }
            ),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")

        if phone and not phone.isdigit():
            raise forms.ValidationError(
                "Phone number must contain numbers only."
            )

        return phone


class NewsletterForm(forms.ModelForm):
    """Form for newsletter subscriptions."""

    class Meta:
        model = NewsletterSubscriber
        fields = ["email"]
        widgets = {
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter your email",
                    "aria-label": "Email address",
                }
            ),
        }
