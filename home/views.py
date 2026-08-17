from django.contrib import messages
from django.shortcuts import render, redirect

from .forms import ContactForm

# Create your views here.


def index(request):
    """ A view to return the index page """
    return render(request, 'home/index.html')


def contact(request):
    """Display and process the customer contact form."""

    if request.method == "POST":
        form = ContactForm(request.POST)

        if form.is_valid():
            form.save()

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

    return render(request, "home/contact.html", context)
