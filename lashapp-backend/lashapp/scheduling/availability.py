"""
Cálculo de horários disponíveis para agendamento público.

Regra: dado um serviço (com sua duração) e uma data, gera os horários
possíveis dentro do expediente da profissional naquele dia da semana,
removendo os que colidem com agendamentos já confirmados ou bloqueios
(TimeOff), e removendo horários que já passaram (se a data for hoje).
"""
from datetime import datetime, timedelta

from django.utils import timezone

from scheduling.models import Appointment, TimeOff, WorkingHours


def get_available_slots(professional, service, target_date):
    """
    Retorna uma lista de `datetime.time` com os horários de início
    disponíveis para `service` na `target_date`, respeitando o expediente,
    agendamentos existentes e bloqueios da `professional`.
    """
    working_hours = WorkingHours.objects.filter(
        professional=professional, weekday=target_date.weekday()
    )
    if not working_hours.exists():
        return []

    duration = timedelta(minutes=service.duration_minutes)

    busy_ranges = _busy_ranges(professional, target_date)

    slots = []
    for wh in working_hours:
        window_start = timezone.make_aware(datetime.combine(target_date, wh.start_time))
        window_end = timezone.make_aware(datetime.combine(target_date, wh.end_time))

        cursor = window_start
        while cursor + duration <= window_end:
            slot_end = cursor + duration
            if not _overlaps_any(cursor, slot_end, busy_ranges):
                slots.append(cursor.time())
            cursor += duration

    if target_date == timezone.localdate():
        now_time = timezone.localtime().time()
        slots = [s for s in slots if s > now_time]

    return slots


def _busy_ranges(professional, target_date):
    day_start = timezone.make_aware(datetime.combine(target_date, datetime.min.time()))
    day_end = day_start + timedelta(days=1)

    appointments = Appointment.objects.filter(
        professional=professional,
        start_datetime__lt=day_end,
        end_datetime__gt=day_start,
    ).exclude(status=Appointment.Status.CANCELLED)

    time_offs = TimeOff.objects.filter(
        professional=professional,
        start_datetime__lt=day_end,
        end_datetime__gt=day_start,
    )

    ranges = [(a.start_datetime, a.end_datetime) for a in appointments]
    ranges += [(t.start_datetime, t.end_datetime) for t in time_offs]
    return ranges


def _overlaps_any(start, end, ranges):
    return any(start < r_end and end > r_start for r_start, r_end in ranges)
