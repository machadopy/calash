from datetime import datetime

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from professionals.models import Professional
from scheduling.models import Appointment, Service


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "name", "description", "duration_minutes", "price"]


class ProfessionalPublicSerializer(serializers.ModelSerializer):
    services = serializers.SerializerMethodField()

    class Meta:
        model = Professional
        fields = ["business_name", "slug", "bio", "instagram", "services"]

    def get_services(self, obj):
        active_services = obj.services.filter(is_active=True)
        return ServiceSerializer(active_services, many=True).data


class AvailabilityQuerySerializer(serializers.Serializer):
    date = serializers.DateField()
    service_id = serializers.IntegerField()

    def validate(self, attrs):
        if attrs["date"] < datetime.now().date():
            raise serializers.ValidationError("A data não pode estar no passado.")
        return attrs


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = [
            "id",
            "professional",
            "service",
            "start_datetime",
            "end_datetime",
            "status",
            "notes",
            "created_at",
        ]
        read_only_fields = ["id", "end_datetime", "status", "created_at"]

    def validate(self, attrs):
        service = attrs["service"]
        professional = attrs["professional"]
        if service.professional_id != professional.id:
            raise serializers.ValidationError(
                {"service": "Este serviço não pertence à profissional informada."}
            )
        return attrs

    def create(self, validated_data):
        validated_data["client"] = self.context["request"].user
        appointment = Appointment(**validated_data)
        try:
            appointment.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict)
        appointment.save()
        return appointment
