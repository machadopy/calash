from datetime import datetime

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from professionals.models import Professional
from scheduling.models import Appointment, Service


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "name", "description", "duration_minutes", "price"]


class ServiceManagementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "name", "description", "duration_minutes", "price", "is_active"]
        read_only_fields = ["id", "is_active"]


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


class AppointmentRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ["service", "start_datetime", "notes"]
        read_only_fields = ["end_datetime", "status"]

    def validate(self, data):
        professional = self.context["professional"]
        service = data["service"]
        start_datetime = data["start_datetime"]

        if service.professional_id != professional.id or not service.is_active:
            raise serializers.ValidationError({"service": "Procedimento inválido para esta profissional."})
        if start_datetime < timezone.now():
            raise serializers.ValidationError({"start_datetime": "Não é possível agendar no passado."})
        if start_datetime > timezone.now() + timedelta(days=30):
            raise serializers.ValidationError({"start_datetime": "O agendamento deve ser feito com no máximo 30 dias de antecedência."})

        end_datetime = start_datetime + timedelta(minutes=service.duration_minutes)
        if Appointment.objects.filter(
            professional=professional,
            start_datetime__lt=end_datetime,
            end_datetime__gt=start_datetime,
        ).exclude(status=Appointment.Status.CANCELLED).exists():
            raise serializers.ValidationError({"start_datetime": "Já existe um agendamento nesse horário."})
        return data

    def create(self, validated_data):
        return Appointment.objects.create(
            professional=self.context["professional"],
            client=self.context["request"].user,
            status=Appointment.Status.PENDING,
            **validated_data,
        )


from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from .models import Appointment, Service

class AppointmentSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)
    service_name = serializers.CharField(source="service.name", read_only=True)

    class Meta:
        model = Appointment
        fields = ['id', 'professional', 'service', 'client_name', 'service_name', 'start_datetime', 'end_datetime', 'status', 'notes']
        # O cliente NUNCA pode enviar essas informações abaixo, o back-end que decide:
        read_only_fields = ['end_datetime', 'status', 'client']

    def validate(self, data):
        user = self.context['request'].user
        start_datetime = data.get('start_datetime')
        service = data.get('service')

        if service and data.get('professional') and service.professional_id != data['professional'].id:
            raise serializers.ValidationError({'service': 'O procedimento não pertence a esta profissional.'})

        # 1. Calcula o horário de término automaticamente com base na duração do serviço
        if start_datetime and service:
            data['end_datetime'] = start_datetime + timedelta(minutes=service.duration_minutes)

            has_conflict = Appointment.objects.filter(
                professional_id=data['professional'].id,
                start_datetime__lt=data['end_datetime'],
                end_datetime__gt=start_datetime,
            ).exclude(status=Appointment.Status.CANCELLED).exists()
            if has_conflict:
                raise serializers.ValidationError(
                    {"start_datetime": "Já existe um agendamento nesse horário."}
                )

        # Regras exclusivas para CLIENTES (A profissional escapa dessas restrições)
        if not user.is_professional:
            
            # 2. Bloqueio de datas no passado
            if start_datetime < timezone.now():
                raise serializers.ValidationError({"start_datetime": "Não é possível agendar no passado."})

            # 3. Limite máximo de 30 dias para frente
            limite_30_dias = timezone.now() + timedelta(days=30)
            if start_datetime > limite_30_dias:
                raise serializers.ValidationError({"start_datetime": "Clientes só podem agendar com no máximo 30 dias de antecedência."})

        return data

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['client'] = user

        # 4. Status Default
        if not user.is_professional:
            # Cliente agendando? Status travado em aguardando_aprovacao
            validated_data['status'] = Appointment.Status.PENDING
        else:
            # Profissional agendando? Ela pode passar o status que quiser, ou assume confirmado
            validated_data['status'] = validated_data.get('status', Appointment.Status.SCHEDULED)

        return super().create(validated_data)