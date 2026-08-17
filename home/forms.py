from django import forms
from .models import ContactMessage


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
