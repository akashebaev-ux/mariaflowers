from django.shortcuts import render


def handler404(request, exception):
    """ Error Handler 404 - Page Not Found """
    return render(request, "errors/404.html", status=404)


def privacy_policy(request):
    """Display the Maria Flowers privacy policy."""
    return render(request, "privacy_policy.html")
