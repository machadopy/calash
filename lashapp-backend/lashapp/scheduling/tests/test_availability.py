from datetime import date, time, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from professionals.models import Professional
from scheduling.availability import get_available_slots
from scheduling.models import Appointment, Service, WorkingHours

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def professional():
    user = User.objects.create_user(
        email="ana@example.com", password="senha123456", name="Ana Lash", is_professional=True
    )
    return Professional.objects.create(user=user, business_name="Ana Lash Design")


@pytest.fixture
def service(professional):
    return Service.objects.create(
        professional=professional, name="Volume Russo", duration_minutes=120, price=180
    )


@pytest.fixture
def client_user():
    return User.objects.create_user(
        email="cliente@example.com", password="senha123456", name="Cliente Teste"
    )


def next_weekday(weekday):
    """Retorna a próxima data (a partir de amanhã) que cai no weekday informado (0=segunda)."""
    today = timezone.localdate()
    days_ahead = (weekday - today.weekday()) % 7
    days_ahead = days_ahead if days_ahead > 0 else 7
    return today + timedelta(days=days_ahead)


class TestAvailableSlots:
    def test_retorna_slots_dentro_do_horario_de_trabalho(self, professional, service):
        target_date = next_weekday(WorkingHours.Weekday.MONDAY)
        WorkingHours.objects.create(
            professional=professional,
            weekday=WorkingHours.Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(11, 0),
        )

        slots = get_available_slots(professional, service, target_date)

        # janela de 9h-11h com serviço de 120min -> só cabe 1 slot: 9h
        assert slots == [time(9, 0)]

    def test_nao_retorna_slots_em_dia_sem_expediente(self, professional, service):
        target_date = next_weekday(WorkingHours.Weekday.SUNDAY)
        WorkingHours.objects.create(
            professional=professional,
            weekday=WorkingHours.Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(18, 0),
        )

        slots = get_available_slots(professional, service, target_date)
        assert slots == []

    def test_remove_slot_ja_ocupado_por_agendamento(self, professional, service, client_user):
        target_date = next_weekday(WorkingHours.Weekday.TUESDAY)
        WorkingHours.objects.create(
            professional=professional,
            weekday=WorkingHours.Weekday.TUESDAY,
            start_time=time(9, 0),
            end_time=time(13, 0),
        )
        booked_start = timezone.make_aware(
            timezone.datetime.combine(target_date, time(9, 0))
        )
        Appointment.objects.create(
            professional=professional,
            client=client_user,
            service=service,
            start_datetime=booked_start,
            end_datetime=booked_start + timedelta(minutes=service.duration_minutes),
        )

        slots = get_available_slots(professional, service, target_date)

        # 9h-13h = 240min / serviço de 120min -> slots possíveis: 9h e 11h; 9h está ocupado
        assert time(9, 0) not in slots
        assert time(11, 0) in slots

    def test_nao_retorna_slots_no_passado_para_hoje(self, professional, service):
        today = timezone.localdate()
        WorkingHours.objects.create(
            professional=professional,
            weekday=today.weekday(),
            start_time=time(0, 0),
            end_time=time(23, 59),
        )

        slots = get_available_slots(professional, service, today)

        now_time = timezone.localtime().time()
        assert all(slot > now_time for slot in slots)
