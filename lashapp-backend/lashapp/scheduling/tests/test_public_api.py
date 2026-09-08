from datetime import time, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from professionals.models import Professional
from scheduling.models import Service, WorkingHours

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
    prof = Professional.objects.create(user=user, business_name="Ana Lash Design")
    Service.objects.create(
        professional=prof, name="Volume Russo", duration_minutes=120, price=180
    )
    return prof


class TestPublicAgendaAPI:
    def test_qualquer_pessoa_ve_perfil_e_servicos_sem_login(self, api_client, professional):
        url = reverse("scheduling-public:agenda-detail", kwargs={"slug": professional.slug})

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["business_name"] == "Ana Lash Design"
        assert len(response.data["services"]) == 1
        assert response.data["services"][0]["name"] == "Volume Russo"

    def test_slug_inexistente_retorna_404(self, api_client):
        url = reverse("scheduling-public:agenda-detail", kwargs={"slug": "nao-existe"})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_profissional_inativa_nao_aparece_na_agenda(self, api_client, professional):
        professional.is_active = False
        professional.save(update_fields=["is_active"])

        url = reverse("scheduling-public:agenda-detail", kwargs={"slug": professional.slug})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_disponibilidade_sem_login(self, api_client, professional):
        service = professional.services.first()
        WorkingHours.objects.create(
            professional=professional,
            weekday=(timezone.localdate() + timedelta(days=7)).weekday(),
            start_time=time(9, 0),
            end_time=time(11, 0),
        )
        target_date = timezone.localdate() + timedelta(days=7)
        url = reverse("scheduling-public:agenda-availability", kwargs={"slug": professional.slug})

        response = api_client.get(url, {"date": target_date.isoformat(), "service_id": service.id})

        assert response.status_code == status.HTTP_200_OK
        assert "09:00" in response.data["slots"]

    def test_disponibilidade_exige_service_id_e_date(self, api_client, professional):
        url = reverse("scheduling-public:agenda-availability", kwargs={"slug": professional.slug})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_disponibilidade_rejeita_data_no_passado(self, api_client, professional):
        service = professional.services.first()
        url = reverse("scheduling-public:agenda-availability", kwargs={"slug": professional.slug})

        response = api_client.get(
            url,
            {
                "date": (timezone.localdate() - timedelta(days=1)).isoformat(),
                "service_id": service.id,
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_disponibilidade_rejeita_servico_de_outra_profissional(self, api_client, professional):
        outra_user = User.objects.create_user(
            email="outra-prof@example.com", password="senha123456", name="Outra", is_professional=True
        )
        outra = Professional.objects.create(user=outra_user, business_name="Outra Lash")
        service = Service.objects.create(
            professional=outra, name="Serviço externo", duration_minutes=60, price=100
        )
        target_date = timezone.localdate() + timedelta(days=7)
        url = reverse("scheduling-public:agenda-availability", kwargs={"slug": professional.slug})

        response = api_client.get(
            url, {"date": target_date.isoformat(), "service_id": service.id}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
