import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

pytestmark = pytest.mark.django_db


class TestCustomUserModel:
    def test_criar_usuario_com_email_e_senha(self):
        User = get_user_model()
        user = User.objects.create_user(
            email="cliente@example.com",
            password="senha-super-segura-123",
            name="Maria Cliente",
        )

        assert user.email == "cliente@example.com"
        assert user.name == "Maria Cliente"
        assert user.check_password("senha-super-segura-123")
        assert user.is_active is True
        assert user.is_staff is False

    def test_email_e_o_campo_de_login(self):
        User = get_user_model()
        assert User.USERNAME_FIELD == "email"

    def test_nao_permite_dois_usuarios_com_mesmo_email(self):
        User = get_user_model()
        User.objects.create_user(email="dup@example.com", password="123456789", name="A")

        with pytest.raises(IntegrityError):
            User.objects.create_user(email="dup@example.com", password="987654321", name="B")

    def test_criar_superusuario(self):
        User = get_user_model()
        admin = User.objects.create_superuser(
            email="admin@example.com", password="admin12345", name="Admin"
        )

        assert admin.is_staff is True
        assert admin.is_superuser is True

    def test_str_retorna_email(self):
        User = get_user_model()
        user = User.objects.create_user(
            email="str@example.com", password="123456789", name="Fulana"
        )
        assert str(user) == "str@example.com"
