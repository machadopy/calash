from rest_framework import generics, permissions

from scheduling.models import Appointment
from scheduling.serializers import AppointmentSerializer


class AppointmentListCreateView(generics.ListCreateAPIView):
    """
    GET  -> lista os agendamentos da própria cliente autenticada.
    POST -> cria um novo agendamento (exige login).
    """

    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Appointment.objects.filter(client=self.request.user)


class AppointmentCancelView(generics.DestroyAPIView):
    """Cancela (soft delete) um agendamento da própria cliente."""

    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Appointment.objects.filter(client=self.request.user)

    def perform_destroy(self, instance):
        instance.status = Appointment.Status.CANCELLED
        instance.save(update_fields=["status", "updated_at"])
