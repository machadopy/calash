from django.shortcuts import redirect


class SuperuserAdminRedirectMiddleware:
    """Envia superusuários para o frontend após o login no Admin."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/admin/" and request.user.is_authenticated and request.user.is_superuser:
            return redirect("/calash/")

        return self.get_response(request)