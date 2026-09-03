import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from professionals.models import Professional

pytestmark = pytest.mark.django_db
User = get_user_model()


def make_user(**kwargs):
    defaults = dict(email="ana@example.com", password="senha123456", name="Ana Lash", is_professional=True)
    defaults.update(kwargs)
    return User.objects.create_user(**defaults)


class TestProfessionalModel:
    def test_criar_profissional_gera_slug_a_partir_do_nome(self):
        user = make_user()
        professional = Professional.objects.create(user=user, business_name="Ana Lash Design")

        assert professional.slug == "ana-lash-design"

    def test_slug_e_unico_mesmo_com_nomes_repetidos(self):
        user1 = make_user(email="ana1@example.com")
        user2 = make_user(email="ana2@example.com")

        p1 = Professional.objects.create(user=user1, business_name="Studio Lash")
        p2 = Professional.objects.create(user=user2, business_name="Studio Lash")

        assert p1.slug != p2.slug
        assert p2.slug.startswith("studio-lash")

    def test_um_usuario_so_pode_ter_um_perfil_profissional(self):
        user = make_user()
        Professional.objects.create(user=user, business_name="Studio A")

        with pytest.raises(IntegrityError):
            Professional.objects.create(user=user, business_name="Studio B")

    def test_str_retorna_business_name(self):
        user = make_user()
        professional = Professional.objects.create(user=user, business_name="Ana Lash Design")
        assert str(professional) == "Ana Lash Design"
