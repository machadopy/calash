from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

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

    def create(self, request, *args, **kwargs):
        if request.user.is_professional:
            return Response(
                {"detail": "A profissional deve gerenciar solicitações pela agenda."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().create(request, *args, **kwargs)

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
    """Cliente cancela o próprio agendamento ou profissional cancela o seu."""

    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_professional:
            return Appointment.objects.filter(professional__user=self.request.user)
        return Appointment.objects.filter(client=self.request.user)

    def perform_destroy(self, instance):
        instance.status = Appointment.Status.CANCELLED
        instance.save(update_fields=["status", "updated_at"])


class AppointmentApproveView(APIView):
    permission_classes = [IsProfessional]

    def patch(self, request, pk):
        appointment = get_object_or_404(
            Appointment, pk=pk, professional__user=request.user
        )
        if appointment.status != Appointment.Status.PENDING:
            return Response(
                {"detail": "Somente solicitações pendentes podem ser aprovadas."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        appointment.status = Appointment.Status.SCHEDULED
        appointment.save(update_fields=["status", "updated_at"])
        return Response(AppointmentSerializer(appointment).data)
