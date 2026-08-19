from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt


def handler404(request, exception):
    """Error Handler 404 - Page Not Found."""
    return render(request, "errors/404.html", status=404)


def privacy_policy(request):
    """Display the Maria Flowers privacy policy."""
    return render(request, "privacy_policy.html")


def terms_conditions(request):
    """Display the Maria Flowers terms and conditions."""
    return render(request, "terms_conditions.html")


def delivery_policy(request):
    """Display the Maria Flowers delivery policy."""
    return render(request, "delivery_policy.html")


def refund_policy(request):
    """Display the Maria Flowers returns and refunds policy."""
    return render(request, "refund_policy.html")


def faq(request):
    """Display the Maria Flowers FAQ page."""
    return render(request, "faq.html")


def about(request):
    """Display the Maria Flowers About Us page."""
    return render(request, "about.html")


@csrf_exempt
def whatsapp_webhook(request):
    """Verify and receive WhatsApp webhook requests."""

    if request.method == "GET":
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        if (
            mode == "subscribe"
            and token == settings.WHATSAPP_VERIFY_TOKEN
        ):
            return HttpResponse(challenge, status=200)

        return HttpResponse("Verification failed", status=403)

    if request.method == "POST":
        # Meta sends WhatsApp events here.
        # We will process incoming messages/videos later.
        return HttpResponse(status=200)

    return HttpResponse(status=405)
