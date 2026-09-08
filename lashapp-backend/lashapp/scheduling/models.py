from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Service(models.Model):
    """Um tipo de procedimento oferecido por uma profissional (ex: Volume Russo)."""

    professional = models.ForeignKey(
        "professionals.Professional", on_delete=models.CASCADE, related_name="services"
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(help_text="Duração do atendimento em minutos.")
    price = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.duration_minutes}min)"


class WorkingHours(models.Model):
    """Janela recorrente de atendimento de uma profissional em um dia da semana."""

    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Segunda-feira"
        TUESDAY = 1, "Terça-feira"
        WEDNESDAY = 2, "Quarta-feira"
        THURSDAY = 3, "Quinta-feira"
        FRIDAY = 4, "Sexta-feira"
        SATURDAY = 5, "Sábado"
        SUNDAY = 6, "Domingo"

    professional = models.ForeignKey(
        "professionals.Professional", on_delete=models.CASCADE, related_name="working_hours"
    )
    weekday = models.IntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ["weekday", "start_time"]
        verbose_name_plural = "working hours"

    def __str__(self):
        return f"{self.get_weekday_display()} {self.start_time}-{self.end_time}"

    def clean(self):
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError("O horário final deve ser depois do horário inicial.")


class TimeOff(models.Model):
    """Bloqueio pontual na agenda (férias, folga, compromisso pessoal)."""

    professional = models.ForeignKey(
        "professionals.Professional", on_delete=models.CASCADE, related_name="time_off"
    )
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    reason = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["start_datetime"]

    def __str__(self):
        return f"Bloqueio {self.start_datetime:%d/%m %H:%M} - {self.end_datetime:%H:%M}"

    def clean(self):
        if self.start_datetime and self.end_datetime and self.start_datetime >= self.end_datetime:
            raise ValidationError("O fim do bloqueio deve ser depois do início.")


class Appointment(models.Model):
    """Um agendamento de uma cliente com a profissional para um serviço."""

    class Status(models.TextChoices):
        PENDING = "pending", "Aguardando aprovação"
        SCHEDULED = "scheduled", "Agendado"
        CANCELLED = "cancelled", "Cancelado"
        COMPLETED = "completed", "Concluído"
        NO_SHOW = "no_show", "Não compareceu"

    professional = models.ForeignKey(
        "professionals.Professional", on_delete=models.CASCADE, related_name="appointments"
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="appointments"
    )
    service = models.ForeignKey(
        Service, on_delete=models.PROTECT, related_name="appointments"
    )
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_datetime"]

    def __str__(self):
        return f"{self.client.name} - {self.service.name} em {self.start_datetime:%d/%m %H:%M}"

    def save(self, *args, **kwargs):
        if not self.end_datetime and self.service_id and self.start_datetime:
            self.end_datetime = self.start_datetime + timedelta(
                minutes=self.service.duration_minutes
            )
        super().save(*args, **kwargs)

    def clean(self):
        errors = {}

        if self.start_datetime and self.start_datetime < timezone.now():
            errors["start_datetime"] = "Não é possível agendar em um horário no passado."

        # calcula end_datetime "on the fly" para validação, sem persistir ainda
        end_datetime = self.end_datetime
        if not end_datetime and self.service_id and self.start_datetime:
            end_datetime = self.start_datetime + timedelta(minutes=self.service.duration_minutes)

        if self.start_datetime and end_datetime and self.professional_id:
            conflicts = Appointment.objects.filter(
                professional_id=self.professional_id,
                start_datetime__lt=end_datetime,
                end_datetime__gt=self.start_datetime,
            ).exclude(status=Appointment.Status.CANCELLED)

            if self.pk:
                conflicts = conflicts.exclude(pk=self.pk)

            if conflicts.exists():
                errors["start_datetime"] = "Já existe um agendamento nesse horário."

        if errors:
            raise ValidationError(errors)
