import base64
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.db import connection
from django.core import mail
from django.core.signing import TimestampSigner
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from professionals.models import Professional
from scheduling.models import Service

pytestmark = pytest.mark.django_db
User = get_user_model()


def user_uid(user):
    return base64.urlsafe_b64encode(str(user.pk).encode()).decode()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def professional():
    user = User.objects.create_user(
        email="profissional@example.com",
        password="senha-forte-123",
        name="Profissional",
        is_professional=True,
        is_email_verified=False,
    )
    return Professional.objects.create(user=user, business_name="Studio")


class TestEmailVerification:
    def test_cadastro_envia_email_de_confirmacao(self, api_client):
        response = api_client.post(
            reverse("users:register"),
            {"email": "nova@example.com", "password": "senha-forte-123", "name": "Nova"},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert len(mail.outbox) == 1
        assert mail.outbox[0].subject == "Confirme seu e-mail"
        assert "confirmar-email?token=" in mail.outbox[0].body

    def test_verify_email_valido_marca_usuario(self, api_client):
        user = User.objects.create_user(
            email="valid@example.com", password="senha-forte-123", name="Valid"
        )
        token = TimestampSigner(salt="users.email-verification").sign_object(
            {"uid": user.pk, "email": user.email}
        )

        response = api_client.post(reverse("users:verify-email"), {"token": token}, format="json")

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.is_email_verified is True

    @pytest.mark.parametrize("token", ["invalid", "expired"])
    def test_verify_email_invalido_ou_expirado_retorna_400(self, api_client, token):
        user = User.objects.create_user(
            email="verify@example.com", password="senha-forte-123", name="Verify"
        )
        if token == "expired":
            with patch(
                "django.core.signing.time.time",
                return_value=timezone.now().timestamp() - timedelta(hours=25).total_seconds(),
            ):
                signed = TimestampSigner(salt="users.email-verification").sign_object(
                    {"uid": user.pk, "email": user.email}
                )
        else:
            signed = token

        response = api_client.post(
            reverse("users:verify-email"), {"token": signed}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_reenvio_exige_login_e_nao_reenvia_para_verificada(self, api_client):
        user = User.objects.create_user(
            email="verified@example.com",
            password="senha-forte-123",
            name="Verified",
            is_email_verified=True,
        )
        api_client.force_authenticate(user=user)

        response = api_client.post(reverse("users:resend-verification"), format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert len(mail.outbox) == 0


class TestPasswordReset:
    def test_forgot_password_tem_mesma_resposta_e_so_envia_para_existente(self, api_client):
        user = User.objects.create_user(
            email="reset@example.com", password="senha-forte-123", name="Reset"
        )

        existing = api_client.post(
            reverse("users:forgot-password"), {"email": user.email}, format="json"
        )
        existing_message = existing.data
        assert existing.status_code == status.HTTP_200_OK
        assert len(mail.outbox) == 1

        mail.outbox.clear()
        missing = api_client.post(
            reverse("users:forgot-password"),
            {"email": "nao-existe@example.com"},
            format="json",
        )
        assert missing.status_code == status.HTTP_200_OK
        assert missing.data == existing_message
        assert len(mail.outbox) == 0

    def test_reset_password_valido_e_token_reutilizado_falha(self, api_client):
        user = User.objects.create_user(
            email="reset-valid@example.com", password="senha-forte-123", name="Reset"
        )
        token = default_token_generator.make_token(user)
        payload = {"uid": user_uid(user), "token": token, "password": "nova-senha-forte-456"}

        response = api_client.post(reverse("users:reset-password"), payload, format="json")
        reused = api_client.post(reverse("users:reset-password"), payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert reused.status_code == status.HTTP_400_BAD_REQUEST
        user.refresh_from_db()
        assert user.check_password("nova-senha-forte-456")

    def test_reset_password_rejeita_token_invalido_e_senha_fraca(self, api_client):
        user = User.objects.create_user(
            email="reset-invalid@example.com", password="senha-forte-123", name="Reset"
        )

        invalid = api_client.post(
            reverse("users:reset-password"),
            {"uid": user_uid(user), "token": "invalid", "password": "nova-senha-forte-456"},
            format="json",
        )
        weak = api_client.post(
            reverse("users:reset-password"),
            {
                "uid": user_uid(user),
                "token": default_token_generator.make_token(user),
                "password": "123",
            },
            format="json",
        )

        assert invalid.status_code == status.HTTP_400_BAD_REQUEST
        assert weak.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in weak.data


class TestEmailAuthRules:
    def test_throttle_de_email_auth(self, api_client):
        from django.core.cache import cache

        cache.clear()
        for _ in range(5):
            response = api_client.post(
                reverse("users:forgot-password"),
                {"email": "throttle@example.com"},
                format="json",
            )
            assert response.status_code == status.HTTP_200_OK

        response = api_client.post(
            reverse("users:forgot-password"),
            {"email": "throttle@example.com"},
            format="json",
        )
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.django_db(transaction=True)
def test_migracao_marca_usuarios_existentes_como_verificados():
    from django.db.migrations.executor import MigrationExecutor

    executor = MigrationExecutor(connection)
    targets = executor.loader.graph.leaf_nodes()
    executor.migrate([("users", "0001_initial")])
    old_user_model = executor.loader.project_state(
        [("users", "0001_initial")]
    ).apps.get_model("users", "CustomUser")
    old_user_model.objects.create(
        email="legacy@example.com",
        name="Legacy",
        password="encoded",
    )

    executor = MigrationExecutor(connection)
    executor.migrate([("users", "0002_customuser_is_email_verified")])
    migrated_user = executor.loader.project_state(
        [("users", "0002_customuser_is_email_verified")]
    ).apps.get_model("users", "CustomUser").objects.get(
        email="legacy@example.com"
    )
    assert migrated_user.is_email_verified is True
    executor.migrate(targets)

    def test_cliente_nao_verificada_nao_pode_agendar(self, api_client, professional):
        client = User.objects.create_user(
            email="booking@example.com",
            password="senha-forte-123",
            name="Booking",
            is_email_verified=False,
        )
        service = Service.objects.create(
            professional=professional,
            name="Volume",
            duration_minutes=60,
            price=100,
        )
        api_client.force_authenticate(user=client)

        response = api_client.post(
            reverse("scheduling:appointment-list"),
            {
                "service": service.pk,
                "start_datetime": (timezone.now() + timedelta(days=2)).isoformat(),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {
            "code": "email_not_verified",
            "detail": "Confirme seu e-mail para agendar.",
        }

    def test_profissional_nao_verificada_pode_agendar_cliente_manual(
        self, api_client, professional
    ):
        service = Service.objects.create(
            professional=professional,
            name="Volume",
            duration_minutes=60,
            price=100,
        )
        api_client.force_authenticate(user=professional.user)

        response = api_client.post(
            reverse("scheduling:appointment-list"),
            {
                "service": service.pk,
                "client_name": "Cliente manual",
                "start_datetime": (timezone.now() + timedelta(days=2)).isoformat(),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
