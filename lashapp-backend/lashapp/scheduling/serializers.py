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


from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from .models import Appointment, Service

class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ['id', 'professional', 'service', 'start_datetime', 'end_datetime', 'status', 'notes']
        # O cliente NUNCA pode enviar essas informações abaixo, o back-end que decide:
        read_only_fields = ['end_datetime', 'status', 'client']

    def validate(self, data):
        user = self.context['request'].user
        start_datetime = data.get('start_datetime')
        service = data.get('service')

        # 1. Calcula o horário de término automaticamente com base na duração do serviço
        if start_datetime and service:
            data['end_datetime'] = start_datetime + timedelta(minutes=service.duration_minutes)

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
            validated_data['status'] = 'aguardando_aprovacao'
        else:
            # Profissional agendando? Ela pode passar o status que quiser, ou assume confirmado
            validated_data['status'] = validated_data.get('status', 'confirmado')

        return super().create(validated_data)