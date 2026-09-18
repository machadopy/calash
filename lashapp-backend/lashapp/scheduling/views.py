from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.permissions import BasePermission
from django.db import transaction
from rest_framework.response import Response
from rest_framework.views import APIView

from scheduling.models import Appointment, Coupon, LunchBreak, Service, WorkingHours
from scheduling.serializers import AppointmentManagementSerializer, AppointmentSerializer, CouponSerializer, LunchBreakSerializer, ProfessionalAppointmentSerializer, ServiceManagementSerializer, WorkingHoursSerializer


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


class ServiceDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ServiceManagementSerializer
    permission_classes = [IsProfessional]

    def get_queryset(self):
        return Service.objects.filter(professional__user=self.request.user)


class CouponListCreateView(generics.ListCreateAPIView):
    serializer_class = CouponSerializer
    permission_classes = [IsProfessional]

    def get_queryset(self):
        return Coupon.objects.filter(professional__user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(professional=self.request.user.professional_profile)


class WorkingHoursView(APIView):
    permission_classes = [IsProfessional]

    def get(self, request):
        working_hours = WorkingHours.objects.filter(
            professional=request.user.professional_profile
        )
        return Response(WorkingHoursSerializer(working_hours, many=True).data)


class LunchBreakView(APIView):
    permission_classes = [IsProfessional]

    def get(self, request):
        date_value = request.query_params.get("date")
        if not date_value:
            return Response({"detail": "Informe date no formato YYYY-MM-DD."}, status=400)
        lunch_break = LunchBreak.objects.filter(
            professional=request.user.professional_profile, date=date_value
        ).first()
        if lunch_break and not lunch_break.is_enabled:
            return Response(None)
        if not lunch_break:
            working_hour = WorkingHours.objects.filter(
                professional=request.user.professional_profile,
                weekday=__import__("datetime").date.fromisoformat(date_value).weekday(),
            ).first()
            if not working_hour or not working_hour.lunch_start_time:
                return Response(None)
            lunch_break = {
                "date": date_value,
                "start_time": working_hour.lunch_start_time,
                "end_time": working_hour.lunch_end_time,
                "is_default": True,
            }
            return Response(lunch_break)
        return Response(LunchBreakSerializer(lunch_break).data)

    def post(self, request):
        serializer = LunchBreakSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        lunch_break, _ = LunchBreak.objects.update_or_create(
            professional=request.user.professional_profile,
            date=serializer.validated_data["date"],
            defaults={
                "start_time": serializer.validated_data["start_time"],
                "end_time": serializer.validated_data["end_time"],
                "is_enabled": True,
            },
        )
        return Response(LunchBreakSerializer(lunch_break).data, status=status.HTTP_201_CREATED)

    def delete(self, request):
        date_value = request.query_params.get("date")
        LunchBreak.objects.update_or_create(
            professional=request.user.professional_profile,
            date=date_value,
            defaults={"start_time": "00:00", "end_time": "00:01", "is_enabled": False},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @transaction.atomic
    def put(self, request):
        serializer = WorkingHoursSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        professional = request.user.professional_profile
        WorkingHours.objects.filter(professional=professional).delete()
        WorkingHours.objects.bulk_create([
            WorkingHours(professional=professional, **item)
            for item in serializer.validated_data
        ])

        working_hours = WorkingHours.objects.filter(professional=professional)
        return Response(WorkingHoursSerializer(working_hours, many=True).data)


class AppointmentListCreateView(generics.ListCreateAPIView):
    """
    GET  -> lista os agendamentos da própria cliente autenticada.
    POST -> cria um novo agendamento (exige login).
    """

    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def get_serializer_class(self):
        if self.request.user.is_professional and self.request.method == "POST":
            return ProfessionalAppointmentSerializer
        return AppointmentSerializer

    def get_queryset(self):
        queryset = Appointment.objects.select_related("client", "service")

        if self.request.user.is_professional:
            queryset = queryset.filter(professional__user=self.request.user).exclude(
                status=Appointment.Status.CANCELLED
            )
        else:
            queryset = queryset.filter(client=self.request.user).exclude(
                status=Appointment.Status.CANCELLED
            )

        selected_date = self.request.query_params.get("date")
        if selected_date:
            queryset = queryset.filter(start_datetime__date=selected_date)

        return queryset


class AppointmentCancelView(generics.RetrieveUpdateDestroyAPIView):
    """Cliente cancela o próprio agendamento ou profissional cancela o seu."""

    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_professional:
            return Appointment.objects.filter(professional__user=self.request.user)
        return Appointment.objects.filter(client=self.request.user)

    def get_serializer_class(self):
        if self.request.user.is_professional and self.request.method in {"PATCH", "PUT"}:
            return AppointmentManagementSerializer
        return AppointmentSerializer

    def partial_update(self, request, *args, **kwargs):
        if not request.user.is_professional:
            return Response({"detail": "Somente a profissional pode editar este agendamento."}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

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


class AppointmentRejectView(APIView):
    permission_classes = [IsProfessional]

    def patch(self, request, pk):
        appointment = get_object_or_404(
            Appointment, pk=pk, professional__user=request.user
        )
        if appointment.status != Appointment.Status.PENDING:
            return Response(
                {"detail": "Somente solicitações pendentes podem ser recusadas."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        appointment.status = Appointment.Status.CANCELLED
        appointment.save(update_fields=["status", "updated_at"])
        return Response(AppointmentSerializer(appointment).data)
