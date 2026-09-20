from django.shortcuts import redirect


class SuperuserAdminRedirectMiddleware:
    """Envia superusuários para o frontend logo após o login no Admin."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        veio_do_login = "/admin/login/" in request.META.get("HTTP_REFERER", "")
        if (
            request.path == "/admin/"
            and veio_do_login
            and request.user.is_authenticated
            and request.user.is_superuser
        ):
            return redirect("/calash/")

        return self.get_response(request)