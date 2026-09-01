from django.http import HttpResponsePermanentRedirect


class RemoveWWWRedirectMiddleware:
    """
    Permanently redirect www.mariaflowers.art to mariaflowers.art.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(":")[0]

        if host == "www.mariaflowers.art":
            new_url = (
                f"https://mariaflowers.art"
                f"{request.get_full_path()}"
            )
            return HttpResponsePermanentRedirect(new_url)

        return self.get_response(request)
