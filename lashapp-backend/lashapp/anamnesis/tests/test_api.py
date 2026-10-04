import base64
import io
from datetime import timedelta

import pytest
from PIL import Image, ImageDraw
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from anamnesis.models import Anamnesis
from professionals.models import Professional
from scheduling.models import Appointment, Service

pytestmark = pytest.mark.django_db
User = get_user_model()


def signature_data_url():
    image = Image.new("RGBA", (160, 60), (255, 255, 255, 0))
    ImageDraw.Draw(image).line((10, 30, 150, 30), fill=(20, 20, 20, 255), width=5)
    content = io.BytesIO()
    image.save(content, format="PNG")
    return "data:image/png;base64," + base64.b64encode(content.getvalue()).decode()


def valid_payload():
    payload = {
        "full_name": "Cliente Teste",
        "birth_date": "1990-01-01",
        "whatsapp": "41999999999",
        "instagram": "@cliente",
        "profession": "Designer",
        "how_met": "Instagram",
        "consent_accepted": True,
        "signed_date": timezone.localdate().isoformat(),
        "signature": signature_data_url(),
    }
    for field in (
        "had_previous_extension", "has_allergies", "uses_contact_lenses", "has_eye_problems",
        "recent_eye_procedure", "thyroid_alopecia_hormonal", "pregnant_or_treatment",
        "pulls_lashes_or_sleeps_prone",
    ):
        payload[field] = False
        payload[f"{field}_notes"] = ""
    return payload


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
def client_user():
    return User.objects.create_user(
        email="cliente@example.com", password="senha123456", name="Cliente Teste"
    )


@pytest.fixture
def service(professional):
    return Service.objects.create(
        professional=professional, name="Volume Russo", duration_minutes=120, price=180
    )


def appointment_payload(professional, service, **anamnesis_changes):
    anamnesis = valid_payload()
    anamnesis.update(anamnesis_changes)
    return {
        "professional": professional.pk,
        "service": service.pk,
        "start_datetime": (timezone.now() + timedelta(days=2)).replace(
            minute=0, second=0, microsecond=0
        ).isoformat(),
        "anamnesis": anamnesis,
    }


def test_agendamento_sem_anamnesis_e_recusado(api_client, professional, service, client_user):
    api_client.force_authenticate(user=client_user)
    payload = appointment_payload(professional, service)
    payload.pop("anamnesis")

    response = api_client.post(reverse("scheduling:appointment-list"), payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert not Appointment.objects.exists()


def test_agendamento_e_ficha_sao_criados_atomicamente(
    api_client, professional, service, client_user, monkeypatch
):
    monkeypatch.setattr("scheduling.serializers.generate_anamnesis_pdf_safely", lambda _: None)
    api_client.force_authenticate(user=client_user)

    response = api_client.post(
        reverse("scheduling:appointment-list"),
        appointment_payload(professional, service),
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    appointment = Appointment.objects.get(client=client_user)
    assert Anamnesis.objects.get(appointment=appointment).professional == professional


def test_ficha_invalida_nao_cria_agendamento(api_client, professional, service, client_user):
    api_client.force_authenticate(user=client_user)
    response = api_client.post(
        reverse("scheduling:appointment-list"),
        appointment_payload(professional, service, consent_accepted=False),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert not Appointment.objects.exists()
    assert not Anamnesis.objects.exists()


@pytest.mark.parametrize("signature", ["", "data:image/png;base64,AAAA"])
def test_assinatura_em_branco_e_recusada(
    api_client, professional, service, client_user, signature
):
    api_client.force_authenticate(user=client_user)
    response = api_client.post(
        reverse("scheduling:appointment-list"),
        appointment_payload(professional, service, signature=signature),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert not Appointment.objects.exists()


def test_signed_date_diferente_de_hoje_e_recusada(api_client, professional, service, client_user):
    api_client.force_authenticate(user=client_user)
    yesterday = (timezone.localdate() - timedelta(days=1)).isoformat()
    response = api_client.post(
        reverse("scheduling:appointment-list"),
        appointment_payload(professional, service, signed_date=yesterday),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert not Appointment.objects.exists()


def test_prefill_devolve_ultima_ficha_sem_data_assinatura_e_consentimento(
    api_client, professional, service, client_user, monkeypatch
):
    monkeypatch.setattr("scheduling.serializers.generate_anamnesis_pdf_safely", lambda _: None)
    api_client.force_authenticate(user=client_user)
    api_client.post(
        reverse("scheduling:appointment-list"),
        appointment_payload(professional, service),
        format="json",
    )

    response = api_client.get(reverse("anamnesis:prefill"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["full_name"] == "Cliente Teste"
    assert response.data["signed_date"] == ""
    assert response.data["signature"] == ""
    assert response.data["consent_accepted"] is False


def test_prefill_retorna_204_sem_ficha_da_propria_cliente(api_client, professional, client_user):
    api_client.force_authenticate(user=client_user)

    response = api_client.get(reverse("anamnesis:prefill"))

    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_cliente_nao_acessa_prefill_de_outra_cliente(
    api_client, professional, service, client_user, monkeypatch
):
    outra_cliente = User.objects.create_user(
        email="outra@example.com", password="senha123456", name="Outra"
    )
    monkeypatch.setattr("scheduling.serializers.generate_anamnesis_pdf_safely", lambda _: None)
    api_client.force_authenticate(user=outra_cliente)
    api_client.post(
        reverse("scheduling:appointment-list"),
        appointment_payload(professional, service),
        format="json",
    )

    api_client.force_authenticate(user=client_user)
    response = api_client.get(reverse("anamnesis:prefill"))

    assert response.status_code == status.HTTP_204_NO_CONTENT
