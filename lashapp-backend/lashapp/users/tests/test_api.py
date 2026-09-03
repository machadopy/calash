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
