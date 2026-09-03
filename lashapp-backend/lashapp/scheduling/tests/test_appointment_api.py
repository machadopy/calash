from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from professionals.models import Professional
from scheduling.models import Appointment, Service

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


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


def future_start():
    return (timezone.now() + timedelta(days=2)).replace(minute=0, second=0, microsecond=0)


class TestAppointmentAPIRequerAuth:
    def test_criar_agendamento_sem_login_retorna_401(self, api_client, professional, service):
        url = reverse("scheduling:appointment-list")
        response = api_client.post(
            url,
            {
                "professional": professional.id,
                "service": service.id,
                "start_datetime": future_start().isoformat(),
            },
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_listar_agendamentos_sem_login_retorna_401(self, api_client):
        url = reverse("scheduling:appointment-list")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAppointmentAPIAutenticado:
    def test_cliente_logada_cria_agendamento(self, api_client, professional, service, client_user):
        api_client.force_authenticate(user=client_user)
        url = reverse("scheduling:appointment-list")

        response = api_client.post(
            url,
            {
                "professional": professional.id,
                "service": service.id,
                "start_datetime": future_start().isoformat(),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert Appointment.objects.filter(client=client_user).exists()

    def test_cliente_so_ve_os_proprios_agendamentos(
        self, api_client, professional, service, client_user
    ):
        outra_cliente = User.objects.create_user(
            email="outra@example.com", password="senha123456", name="Outra"
        )
        start = future_start()
        Appointment.objects.create(
            professional=professional,
            client=client_user,
            service=service,
            start_datetime=start,
            end_datetime=start + timedelta(minutes=service.duration_minutes),
        )
        Appointment.objects.create(
            professional=professional,
            client=outra_cliente,
            service=service,
            start_datetime=start + timedelta(days=1),
            end_datetime=start + timedelta(days=1, minutes=service.duration_minutes),
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("scheduling:appointment-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"] if "results" in response.data else response.data
        assert len(results) == 1

    def test_cliente_cancela_o_proprio_agendamento(
        self, api_client, professional, service, client_user
    ):
        start = future_start()
        appointment = Appointment.objects.create(
            professional=professional,
            client=client_user,
            service=service,
            start_datetime=start,
            end_datetime=start + timedelta(minutes=service.duration_minutes),
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("scheduling:appointment-detail", kwargs={"pk": appointment.pk})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        appointment.refresh_from_db()
        assert appointment.status == Appointment.Status.CANCELLED

    def test_cliente_nao_pode_cancelar_agendamento_de_outra(
        self, api_client, professional, service, client_user
    ):
        outra_cliente = User.objects.create_user(
            email="outra2@example.com", password="senha123456", name="Outra2"
        )
        start = future_start()
        appointment = Appointment.objects.create(
            professional=professional,
            client=outra_cliente,
            service=service,
            start_datetime=start,
            end_datetime=start + timedelta(minutes=service.duration_minutes),
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("scheduling:appointment-detail", kwargs={"pk": appointment.pk})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_nao_cria_agendamento_conflitante_via_api(
        self, api_client, professional, service, client_user
    ):
        start = future_start()
        Appointment.objects.create(
            professional=professional,
            client=client_user,
            service=service,
            start_datetime=start,
            end_datetime=start + timedelta(minutes=service.duration_minutes),
        )

        api_client.force_authenticate(user=client_user)
        url = reverse("scheduling:appointment-list")
        response = api_client.post(
            url,
            {
                "professional": professional.id,
                "service": service.id,
                "start_datetime": start.isoformat(),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
