from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from professionals.models import Professional
from scheduling.availability import get_available_slots, get_lunch_interval
from scheduling.models import Service
from scheduling.serializers import (
    AppointmentRequestSerializer,
    AvailabilityQuerySerializer,
    ProfessionalPublicSerializer,
    WorkingHoursSerializer,
)
from scheduling.models import Appointment, WorkingHours
from django.utils import timezone
from datetime import datetime, time, timedelta


class ProfessionalAgendaView(generics.RetrieveAPIView):
    """Perfil público da profissional + lista de serviços. Não exige login."""

    serializer_class = ProfessionalPublicSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"
    queryset = Professional.objects.filter(is_active=True)


class AvailabilityView(APIView):
    """Horários livres para um serviço numa data. Não exige login."""

    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        professional = get_object_or_404(Professional, slug=slug, is_active=True)

        query = AvailabilityQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        service = get_object_or_404(
            Service, id=query.validated_data["service_id"], professional=professional
        )

        slots = get_available_slots(professional, service, query.validated_data["date"])

        return Response({"slots": [s.strftime("%H:%M") for s in slots]})


class PublicWorkingHoursView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        professional = get_object_or_404(Professional, slug=slug, is_active=True)
        working_hours = WorkingHours.objects.filter(professional=professional)
        return Response(WorkingHoursSerializer(working_hours, many=True).data)


class PublicScheduleView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        professional = get_object_or_404(Professional, slug=slug, is_active=True)
        try:
            date_obj = datetime.strptime(request.query_params["date"], "%Y-%m-%d").date()
        except (KeyError, ValueError):
            return Response({"detail": "Informe date no formato YYYY-MM-DD."}, status=400)

        working_hours = WorkingHours.objects.filter(
            professional=professional, weekday=date_obj.weekday()
        )
        start_of_day = timezone.make_aware(datetime.combine(date_obj, time.min))
        end_of_day = timezone.make_aware(datetime.combine(date_obj, time.max))
        appointments = Appointment.objects.filter(
            professional=professional,
            start_datetime__lt=end_of_day,
            end_datetime__gt=start_of_day,
        ).exclude(status=Appointment.Status.CANCELLED)
        lunch_interval = get_lunch_interval(professional, date_obj, appointments)

        slots = []
        for working_hour in working_hours:
            current = datetime.combine(date_obj, working_hour.start_time)
            end = datetime.combine(date_obj, working_hour.end_time)
            while current < end:
                slot_start = timezone.make_aware(current)
                slot_end = slot_start + timedelta(hours=1)
                lunch_start = timezone.make_aware(datetime.combine(date_obj, lunch_interval[0])) if lunch_interval else None
                lunch_end = timezone.make_aware(datetime.combine(date_obj, lunch_interval[1])) if lunch_interval else None
                occupied = any(
                    appointment.start_datetime < slot_end
                    and appointment.end_datetime > slot_start
                    for appointment in appointments
                )
                occupied = occupied or (lunch_start and lunch_end and slot_start < lunch_end and slot_end > lunch_start)
                slots.append({
                    "time": current.strftime("%H:%M"),
                    "available": not occupied,
                    "is_lunch": bool(lunch_start and lunch_end and slot_start < lunch_end and slot_end > lunch_start),
                })
                current += timedelta(hours=1)

        return Response({
            "slots": slots,
            "lunch": {
                "start_time": lunch_interval[0].strftime("%H:%M"),
                "end_time": lunch_interval[1].strftime("%H:%M"),
            } if lunch_interval else None,
        })


class PublicAppointmentCreateView(generics.CreateAPIView):
    """Cria uma solicitação para a profissional identificada pelo slug."""

    serializer_class = AppointmentRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["professional"] = get_object_or_404(
            Professional, slug=self.kwargs["slug"], is_active=True
        )
        return context
