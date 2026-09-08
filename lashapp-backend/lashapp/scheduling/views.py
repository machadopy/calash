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
        queryset = Appointment.objects.select_related("client", "service")

        if self.request.user.is_professional:
            queryset = queryset.filter(professional__user=self.request.user)
        else:
            queryset = queryset.filter(client=self.request.user)

        selected_date = self.request.query_params.get("date")
        if selected_date:
            queryset = queryset.filter(start_datetime__date=selected_date)

        return queryset


class AppointmentCancelView(generics.DestroyAPIView):
    """Cancela (soft delete) um agendamento da própria cliente."""

    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Appointment.objects.filter(client=self.request.user)

    def perform_destroy(self, instance):
        instance.status = Appointment.Status.CANCELLED
        instance.save(update_fields=["status", "updated_at"])
