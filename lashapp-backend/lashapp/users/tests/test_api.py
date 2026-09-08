import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


class TestRegisterAPI:
    def test_registrar_nova_cliente_com_sucesso(self, api_client):
        url = reverse("users:register")
        payload = {
            "email": "nova@example.com",
            "password": "senha-forte-123",
            "name": "Nova Cliente",
            "phone": "41999999999",
        }

        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(email="nova@example.com").exists()
        # senha não deve vazar na resposta
        assert "password" not in response.data

    def test_nao_registra_email_duplicado(self, api_client):
        User.objects.create_user(email="dup@example.com", password="123456789", name="A")
        url = reverse("users:register")

        response = api_client.post(
            url,
            {"email": "dup@example.com", "password": "outrasenha123", "name": "B"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_senha_curta_e_rejeitada(self, api_client):
        url = reverse("users:register")
        response = api_client.post(
            url, {"email": "fraca@example.com", "password": "123", "name": "Fraca"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_retorna_tokens_jwt(self, api_client):
        User.objects.create_user(
            email="login@example.com", password="senha-forte-123", name="Login Teste"
        )
        url = reverse("users:token_obtain_pair")

        response = api_client.post(
            url, {"email": "login@example.com", "password": "senha-forte-123"}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_refresh_retorna_novo_access_token(self, api_client):
        User.objects.create_user(
            email="refresh@example.com", password="senha-forte-123", name="Refresh Teste"
        )
        login = api_client.post(
            reverse("users:token_obtain_pair"),
            {"email": "refresh@example.com", "password": "senha-forte-123"},
            format="json",
        )

        response = api_client.post(
            reverse("users:token_refresh"), {"refresh": login.data["refresh"]}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_login_com_credenciais_invalidas_retorna_401(self, api_client):
        response = api_client.post(
            reverse("users:token_obtain_pair"),
            {"email": "inexistente@example.com", "password": "senha-errada"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestMeAPI:
    def test_me_exige_autenticacao(self, api_client):
        response = api_client.get(reverse("users:me"))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_retorna_dados_da_usuario_logada(self, api_client):
        user = User.objects.create_user(
            email="me@example.com", password="senha-forte-123", name="Minha Conta", phone="41999999999"
        )
        api_client.force_authenticate(user=user)

        response = api_client.get(reverse("users:me"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == user.email
        assert response.data["name"] == "Minha Conta"
        assert response.data["phone"] == "41999999999"
        assert "password" not in response.data

    def test_me_atualiza_apenas_dados_permitidos(self, api_client):
        user = User.objects.create_user(
            email="update@example.com", password="senha-forte-123", name="Nome Antigo"
        )
        api_client.force_authenticate(user=user)

        response = api_client.patch(
            reverse("users:me"), {"name": "Nome Novo", "phone": "41888888888"}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.name == "Nome Novo"
        assert user.phone == "41888888888"

    def test_me_nao_permite_alterar_perfil_profissional(self, api_client):
        user = User.objects.create_user(
            email="client@example.com", password="senha-forte-123", name="Cliente"
        )
        api_client.force_authenticate(user=user)

        response = api_client.patch(
            reverse("users:me"), {"is_professional": True}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.is_professional is False
