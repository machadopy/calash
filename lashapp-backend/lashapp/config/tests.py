from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.http import HttpResponse

from config.middleware import SuperuserAdminRedirectMiddleware


class SuperuserAdminRedirectMiddlewareTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def get_response(self, request):
        middleware = SuperuserAdminRedirectMiddleware(
            lambda received_request: HttpResponse("ok")
        )
        return middleware(request)

    def test_superusuario_autenticado_e_redirecionado_apos_login_admin(self):
        user = get_user_model().objects.create_superuser(
            email="admin@example.com",
            password="senha123",
            name="Administrador",
        )
        request = self.factory.get("/admin/", HTTP_REFERER="http://testserver/admin/login/")
        request.user = user

        response = self.get_response(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/calash/")

    def test_usuario_comum_nao_e_redirecionado(self):
        user = get_user_model().objects.create_user(
            email="comum@example.com",
            password="senha123",
            name="Usuario Comum",
        )
        request = self.factory.get("/admin/", HTTP_REFERER="http://testserver/admin/login/")
        request.user = user

        response = self.get_response(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")
