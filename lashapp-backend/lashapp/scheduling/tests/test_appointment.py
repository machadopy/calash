from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from professionals.models import Professional
from scheduling.models import Appointment, Service

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def professional():
    user = User.objects.create_user(
        email="ana@example.com", password="senha123456", name="Ana Lash", is_professional=True
    )
    return Professional.objects.create(user=user, business_name="Ana Lash Design")


@pytest.fixture
def client_user():
    return User.objects.create_user(
        email="cliente@example.com", password="senha123456", name="Cliente Teste"
    )


@pytest.fixture
def service(professional):
    return Service.objects.create(
        professional=professional, name="Volume Russo", duration_minutes=120, price=180
    )


def future_datetime(hours_from_now=48):
    # próximo horário "redondo", sempre no futuro, evitando flakiness de teste
    base = timezone.now() + timedelta(hours=hours_from_now)
    return base.replace(minute=0, second=0, microsecond=0)


class TestAppointmentModel:
    def test_end_datetime_e_calculado_a_partir_da_duracao_do_servico(
        self, professional, client_user, service
    ):
        start = future_datetime()
        appointment = Appointment(
            professional=professional,
            client=client_user,
            service=service,
            start_datetime=start,
        )
        appointment.full_clean()
        appointment.save()

        assert appointment.end_datetime == start + timedelta(minutes=120)

    def test_nao_permite_agendar_no_passado(self, professional, client_user, service):
        past = timezone.now() - timedelta(days=1)
        appointment = Appointment(
            professional=professional, client=client_user, service=service, start_datetime=past
        )
        with pytest.raises(ValidationError):
            appointment.full_clean()

    def test_nao_permite_dois_agendamentos_sobrepostos_para_mesma_profissional(
        self, professional, client_user, service
    ):
        start = future_datetime()
        Appointment.objects.create(
            professional=professional,
            client=client_user,
            service=service,
            start_datetime=start,
            end_datetime=start + timedelta(minutes=service.duration_minutes),
        )

        # novo agendamento começa 30min depois do primeiro (ainda dentro da duração de 120min)
        overlapping_start = start + timedelta(minutes=30)
        second = Appointment(
            professional=professional,
            client=client_user,
            service=service,
            start_datetime=overlapping_start,
        )

        with pytest.raises(ValidationError):
            second.full_clean()

    def test_permite_agendamento_logo_apos_o_fim_do_anterior(
        self, professional, client_user, service
    ):
        start = future_datetime()
        Appointment.objects.create(
            professional=professional,
            client=client_user,
            service=service,
            start_datetime=start,
            end_datetime=start + timedelta(minutes=service.duration_minutes),
        )

        next_start = start + timedelta(minutes=service.duration_minutes)
        second = Appointment(
            professional=professional,
            client=client_user,
            service=service,
            start_datetime=next_start,
        )
        # não deve levantar exceção
        second.full_clean()

    def test_agendamento_cancelado_nao_bloqueia_horario(
        self, professional, client_user, service
    ):
        start = future_datetime()
        cancelled = Appointment.objects.create(
            professional=professional,
            client=client_user,
            service=service,
            start_datetime=start,
            end_datetime=start + timedelta(minutes=service.duration_minutes),
            status=Appointment.Status.CANCELLED,
        )
        assert cancelled.status == Appointment.Status.CANCELLED

        second = Appointment(
            professional=professional, client=client_user, service=service, start_datetime=start
        )
        # como o primeiro está cancelado, este não deve conflitar
        second.full_clean()

    def test_str_appointment(self, professional, client_user, service):
        start = future_datetime()
        appointment = Appointment(
            professional=professional,
            client=client_user,
            service=service,
            start_datetime=start,
        )
        appointment.full_clean()
        appointment.save()
        assert "Cliente Teste" in str(appointment)
        assert "Volume Russo" in str(appointment)
