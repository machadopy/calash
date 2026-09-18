from datetime import datetime

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from django.contrib.auth import get_user_model
from professionals.models import Professional
from scheduling.models import Appointment, Coupon, LunchBreak, Service, WorkingHours


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "name", "description", "duration_minutes", "price"]


class ServiceManagementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "name", "description", "duration_minutes", "price", "is_active"]
        read_only_fields = ["id", "is_active"]


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = ["id", "code", "discount_type", "discount_value", "is_active"]
        read_only_fields = ["id", "is_active"]

    def validate_code(self, value):
        return value.strip().upper()

    def validate(self, attrs):
        if attrs["discount_value"] <= 0:
            raise serializers.ValidationError({"discount_value": "O desconto deve ser maior que zero."})
        if (
            attrs["discount_type"] == Coupon.DiscountType.PERCENTAGE
            and attrs["discount_value"] > 100
        ):
            raise serializers.ValidationError(
                {"discount_value": "O desconto percentual não pode ser maior que 100."}
            )
        return attrs


class WorkingHoursSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkingHours
        fields = ["id", "weekday", "start_time", "end_time", "lunch_start_time", "lunch_end_time", "slot_interval_minutes"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        if attrs["start_time"] >= attrs["end_time"]:
            raise serializers.ValidationError({"end_time": "O fim deve ser depois do início."})
        if attrs.get("lunch_start_time") and attrs.get("lunch_end_time"):
            if attrs["lunch_start_time"] >= attrs["lunch_end_time"]:
                raise serializers.ValidationError({"lunch_end_time": "O fim do almoço deve ser depois do início."})
            if attrs["lunch_start_time"] < attrs["start_time"] or attrs["lunch_end_time"] > attrs["end_time"]:
                raise serializers.ValidationError({"lunch_start_time": "O almoço deve estar dentro do expediente."})
        return attrs


class LunchBreakSerializer(serializers.ModelSerializer):
    class Meta:
        model = LunchBreak
        fields = ["date", "start_time", "end_time"]

    def validate(self, attrs):
        if attrs["start_time"] >= attrs["end_time"]:
            raise serializers.ValidationError({"end_time": "O fim do almoço deve ser depois do início."})
        professional = self.context["request"].user.professional_profile
        working_hour = WorkingHours.objects.filter(
            professional=professional, weekday=attrs["date"].weekday()
        ).first()
        if not working_hour or attrs["start_time"] < working_hour.start_time or attrs["end_time"] > working_hour.end_time:
            raise serializers.ValidationError({"start_time": "O almoço deve estar dentro do expediente."})
        start = timezone.make_aware(datetime.combine(attrs["date"], attrs["start_time"]))
        end = timezone.make_aware(datetime.combine(attrs["date"], attrs["end_time"]))
        if Appointment.objects.filter(
            professional=professional,
            start_datetime__lt=end,
            end_datetime__gt=start,
        ).exclude(status=Appointment.Status.CANCELLED).exists():
            raise serializers.ValidationError({"start_time": "Esse horário já possui um agendamento."})
        return attrs


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


class ProfessionalAppointmentSerializer(serializers.ModelSerializer):
    client = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.filter(is_professional=False))

    class Meta:
        model = Appointment
        fields = ["client", "service", "start_datetime", "notes"]

    def validate(self, data):
        professional = self.context["request"].user.professional_profile
        if data["service"].professional_id != professional.id:
            raise serializers.ValidationError({"service": "Procedimento inválido para esta profissional."})
        if data["start_datetime"] < timezone.now():
            raise serializers.ValidationError({"start_datetime": "Não é possível agendar no passado."})
        end = data["start_datetime"] + timedelta(minutes=data["service"].duration_minutes)
        if Appointment.objects.filter(professional=professional, start_datetime__lt=end, end_datetime__gt=data["start_datetime"]).exclude(status=Appointment.Status.CANCELLED).exists():
            raise serializers.ValidationError({"start_datetime": "Já existe um agendamento nesse horário."})
        return data

    def create(self, validated_data):
        return Appointment.objects.create(
            professional=self.context["request"].user.professional_profile,
            status=Appointment.Status.SCHEDULED,
            **validated_data,
        )


from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from .models import Appointment, Service

class AppointmentSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)
    service_name = serializers.CharField(source="service.name", read_only=True)
    service_duration_minutes = serializers.SerializerMethodField()
    additional_service_ids = serializers.PrimaryKeyRelatedField(
        source="additional_services", many=True, read_only=True
    )

    class Meta:
        model = Appointment
        fields = ['id', 'professional', 'service', 'client_name', 'service_name', 'service_duration_minutes', 'additional_service_ids', 'start_datetime', 'end_datetime', 'status', 'notes']
        # O cliente NUNCA pode enviar essas informações abaixo, o back-end que decide:
        read_only_fields = ['end_datetime', 'status', 'client']

    def get_service_duration_minutes(self, obj):
        return obj.total_duration_minutes

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


class AppointmentManagementSerializer(serializers.ModelSerializer):
    additional_services = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Service.objects.all(), required=False
    )

    class Meta:
        model = Appointment
        fields = ["id", "duration_minutes_override", "additional_services"]

    def validate(self, attrs):
        professional = self.context["request"].user.professional_profile
        additional = attrs.get("additional_services", list(self.instance.additional_services.all()))
        if any(service.professional_id != professional.id for service in additional):
            raise serializers.ValidationError({"additional_services": "Procedimento inválido para esta profissional."})
        if self.instance.service.professional_id != professional.id:
            raise serializers.ValidationError("Agendamento inválido para esta profissional.")
        return attrs

    def update(self, instance, validated_data):
        additional = validated_data.pop("additional_services", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.end_datetime = None
        instance.save()
        if additional is not None:
            instance.additional_services.set(additional)
            instance.end_datetime = None
            instance.save(update_fields=["end_datetime", "updated_at"])
        else:
            instance.end_datetime = None
            instance.save(update_fields=["end_datetime", "updated_at"])
        return instance