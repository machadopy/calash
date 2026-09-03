from datetime import time

import pytest
from django.contrib.auth import get_user_model

from professionals.models import Professional
from scheduling.models import Service, WorkingHours

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def professional():
    user = User.objects.create_user(
        email="ana@example.com", password="senha123456", name="Ana Lash", is_professional=True
    )
    return Professional.objects.create(user=user, business_name="Ana Lash Design")


class TestServiceModel:
    def test_criar_servico(self, professional):
        service = Service.objects.create(
            professional=professional,
            name="Volume Russo",
            duration_minutes=120,
            price=180.00,
        )
        assert service.name == "Volume Russo"
        assert service.duration_minutes == 120
        assert service.is_active is True

    def test_str_retorna_nome_e_duracao(self, professional):
        service = Service.objects.create(
            professional=professional, name="Volume Fio a Fio", duration_minutes=90, price=120
        )
        assert str(service) == "Volume Fio a Fio (90min)"


class TestWorkingHoursModel:
    def test_criar_horario_de_trabalho(self, professional):
        wh = WorkingHours.objects.create(
            professional=professional,
            weekday=WorkingHours.Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(18, 0),
        )
        assert wh.weekday == 0
        assert wh.start_time == time(9, 0)

    def test_nao_permite_horario_final_antes_do_inicial(self, professional):
        from django.core.exceptions import ValidationError

        wh = WorkingHours(
            professional=professional,
            weekday=WorkingHours.Weekday.TUESDAY,
            start_time=time(18, 0),
            end_time=time(9, 0),
        )
        with pytest.raises(ValidationError):
            wh.full_clean()
