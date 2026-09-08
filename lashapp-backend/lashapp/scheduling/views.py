from rest_framework import generics, permissions
from rest_framework.permissions import BasePermission

from scheduling.models import Appointment, Service
from scheduling.serializers import AppointmentSerializer, ServiceManagementSerializer


class IsProfessional(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user.is_authenticated
            and request.user.is_professional
            and hasattr(request.user, "professional_profile")
        )


class ServiceListCreateView(generics.ListCreateAPIView):
    serializer_class = ServiceManagementSerializer
    permission_classes = [IsProfessional]

    def get_queryset(self):
        return Service.objects.filter(professional__user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(professional=self.request.user.professional_profile)


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
