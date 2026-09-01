from django import forms
from .models import Order, Review, ReviewImage


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = (
            'full_name',
            'email',
            'phone_number',
            'street_address1',
            'street_address2',
            'town_or_city',
            'postcode',
            'country',
            'county',
        )

    def __init__(self, *args, **kwargs):
        """
        Add placeholders and classes, remove auto-generated
        labels and set autofocus on first field.
        """
        super().__init__(*args, **kwargs)

        placeholders = {
            'full_name': 'Full Name',
            'email': 'Email Address',
            'phone_number': 'Phone Number',
            'postcode': 'Postal Code',
            'town_or_city': 'Town or City',
            'street_address1': 'Street Address 1',
            'street_address2': 'Street Address 2',
            'county': 'County, State or Locality',
        }

        self.fields['full_name'].widget.attrs['autofocus'] = True

        # Only digits are allowed in the phone number field.
        self.fields['phone_number'].widget.attrs.update({
            'type': 'tel',
            'inputmode': 'numeric',
            'pattern': '[0-9]+',
            'title': 'Please enter numbers only.',
        })

        for field in self.fields:
            if field != 'country':
                if self.fields[field].required:
                    placeholder = f'{placeholders[field]} *'
                else:
                    placeholder = placeholders[field]

                self.fields[field].widget.attrs[
                    'placeholder'
                ] = placeholder

            self.fields[field].widget.attrs[
                'class'
            ] = 'stripe-style-input'

            self.fields[field].label = False

    def clean_phone_number(self):
        """
        Ensure the phone number contains digits only.
        """
        phone_number = self.cleaned_data.get('phone_number', '').strip()

        if not phone_number.isdigit():
            raise forms.ValidationError(
                'Phone number must contain numbers only.'
            )

        return phone_number


class ReviewForm(forms.ModelForm):
    """
    Form for customers to submit a rating and optional review.
    """

    RATING_CHOICES = [
        (1, "1 - Poor"),
        (2, "2 - Fair"),
        (3, "3 - Good"),
        (4, "4 - Very Good"),
        (5, "5 - Excellent"),
    ]

    rating = forms.TypedChoiceField(
        choices=RATING_CHOICES,
        coerce=int,
        widget=forms.RadioSelect,
        label="Your Rating",
    )

    class Meta:
        model = Review
        fields = (
            "rating",
            "comment",
        )

        widgets = {
            "comment": forms.Textarea(
                attrs={
                    "class": "maria-review-textarea",
                    "rows": 6,
                    "maxlength": 1000,
                    "placeholder": (
                        "Tell us about your flowers, "
                        "delivery and overall experience..."
                    ),
                }
            ),
        }

        labels = {
            "comment": "Your Review (Optional)",
        }


class ReviewImageForm(forms.ModelForm):
    """
    Form for uploading an optional review image.
    """

    class Meta:
        model = ReviewImage
        fields = (
            "image",
        )

        widgets = {
            "image": forms.ClearableFileInput(
                attrs={
                    "class": "maria-review-image-input",
                    "accept": "image/jpeg,image/png,image/webp",
                }
            ),
        }

        labels = {
            "image": "Bouquet Photo (Optional)",
        }
