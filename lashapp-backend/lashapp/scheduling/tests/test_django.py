from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase, APIRequestFactory

from professionals.models import Professional
from scheduling.availability import get_available_slots
from scheduling.models import Appointment, Service, WorkingHours
from scheduling.public_views import SupportContactView


User = get_user_model()


class AppointmentConflictTestCase(TestCase):
    def setUp(self):
        professional_user = User.objects.create_user(
            email="profissional@example.com",
            password="senha123",
            name="Profissional",
            is_professional=True,
        )
        self.professional = Professional.objects.create(
            user=professional_user,
            business_name="Calash Studio",
        )
        self.client_user = User.objects.create_user(
            email="cliente@example.com",
            password="senha123",
            name="Cliente",
        )
        self.service = Service.objects.create(
            professional=self.professional,
            name="Volume Russo",
            duration_minutes=120,
            price=180,
        )

    def test_rejeita_agendamento_sobreposto(self):
        start = timezone.now() + timedelta(days=2)
        start = start.replace(minute=0, second=0, microsecond=0)
        Appointment.objects.create(
            professional=self.professional,
            client=self.client_user,
            service=self.service,
            start_datetime=start,
            end_datetime=start + timedelta(minutes=120),
        )

        overlapping = Appointment(
            professional=self.professional,
            client=self.client_user,
            service=self.service,
            start_datetime=start + timedelta(minutes=30),
        )

        with self.assertRaises(ValidationError):
            overlapping.full_clean()

    def test_permite_agendamento_logo_apos_o_anterior(self):
        start = timezone.now() + timedelta(days=2)
        start = start.replace(minute=0, second=0, microsecond=0)
        Appointment.objects.create(
            professional=self.professional,
            client=self.client_user,
            service=self.service,
            start_datetime=start,
            end_datetime=start + timedelta(minutes=120),
        )

        adjacent = Appointment(
            professional=self.professional,
            client=self.client_user,
            service=self.service,
            start_datetime=start + timedelta(minutes=120),
        )
        adjacent.full_clean()


class AvailableSlotsTestCase(TestCase):
    def setUp(self):
        professional_user = User.objects.create_user(
            email="slots@example.com",
            password="senha123",
            name="Profissional",
            is_professional=True,
        )
        self.professional = Professional.objects.create(
            user=professional_user,
            business_name="Studio Slots",
        )
        self.service = Service.objects.create(
            professional=self.professional,
            name="Alongamento",
            duration_minutes=120,
            price=200,
        )

    def test_slots_respeitam_expediente_e_servico(self):
        target_date = timezone.localdate() + timedelta(days=7)
        WorkingHours.objects.create(
            professional=self.professional,
            weekday=target_date.weekday(),
            start_time=time(9, 0),
            end_time=time(11, 0),
            slot_interval_minutes=60,
        )

        slots = get_available_slots(self.professional, self.service, target_date)

        self.assertEqual(slots, [time(9, 0)])

    def test_slot_ja_agendado_e_removido(self):
        target_date = timezone.localdate() + timedelta(days=7)
        WorkingHours.objects.create(
            professional=self.professional,
            weekday=target_date.weekday(),
            start_time=time(9, 0),
            end_time=time(13, 0),
            slot_interval_minutes=60,
        )
        start = timezone.make_aware(
            timezone.datetime.combine(target_date, time(9, 0))
        )
        client = User.objects.create_user(
            email="slotcliente@example.com",
            password="senha123",
            name="Cliente Slots",
        )
        Appointment.objects.create(
            professional=self.professional,
            client=client,
            service=self.service,
            start_datetime=start,
            end_datetime=start + timedelta(minutes=120),
        )

        slots = get_available_slots(self.professional, self.service, target_date)

        self.assertNotIn(time(9, 0), slots)
        self.assertIn(time(11, 0), slots)


class WhatsAppNormalizationUnitTestCase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def get_response(self, number):
        with override_settings(SUPPORT_WHATSAPP_NUMBER=number):
            request = self.factory.get("/api/public/support/")
            response = SupportContactView.as_view()(request)
            response.render()
            return response

    def test_numero_vazio(self):
        response = self.get_response("")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["whatsapp_number"], "")
        self.assertIsNone(response.data["whatsapp_url"])

    def test_numero_formatado(self):
        response = self.get_response("55 (41) 98454-1254")
        self.assertEqual(response.data["whatsapp_number"], "5541984541254")
        self.assertEqual(response.data["whatsapp_url"], "https://wa.me/5541984541254")

    def test_numero_so_com_digitos(self):
        response = self.get_response("41984541254")
        self.assertEqual(response.data["whatsapp_number"], "41984541254")
        self.assertEqual(response.data["whatsapp_url"], "https://wa.me/41984541254")


class PublicSupportContactTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()

    def test_endpoint_retorna_numero_publico(self):
        with override_settings(SUPPORT_WHATSAPP_NUMBER="55 (41) 98454-1254"):
            response = self.client.get(reverse("scheduling-public:support-contact"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["whatsapp_number"], "5541984541254")
        self.assertEqual(response.data["whatsapp_url"], "https://wa.me/5541984541254")

    def test_endpoint_retorna_numero_vazio(self):
        with override_settings(SUPPORT_WHATSAPP_NUMBER=""):
            response = self.client.get(reverse("scheduling-public:support-contact"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["whatsapp_number"], "")
        self.assertIsNone(response.data["whatsapp_url"])
