from datetime import datetime, timedelta, time
from django.utils import timezone
from .models import Appointment, WorkingHours, TimeOff


def get_available_slots(professional, service, date_obj):
    """Retorna os horários de início livres para um serviço na data informada."""
    weekday = date_obj.weekday()
    now = timezone.now()
    slots = []

    day_start = timezone.make_aware(datetime.combine(date_obj, time.min))
    day_end = timezone.make_aware(datetime.combine(date_obj, time.max))
    appointments = Appointment.objects.filter(
        professional=professional,
        start_datetime__lt=day_end,
        end_datetime__gt=day_start,
    ).exclude(status=Appointment.Status.CANCELLED)
    time_off = TimeOff.objects.filter(
        professional=professional,
        start_datetime__lt=day_end,
        end_datetime__gt=day_start,
    )

    for working_hour in WorkingHours.objects.filter(
        professional=professional, weekday=weekday
    ):
        current = datetime.combine(date_obj, working_hour.start_time)
        end = datetime.combine(date_obj, working_hour.end_time)
        while current + timedelta(minutes=service.duration_minutes) <= end:
            slot_start = timezone.make_aware(current)
            slot_end = slot_start + timedelta(minutes=service.duration_minutes)
            blocked = any(
                appointment.start_datetime < slot_end and appointment.end_datetime > slot_start
                for appointment in appointments
            ) or any(
                blocked_period.start_datetime < slot_end
                and blocked_period.end_datetime > slot_start
                for blocked_period in time_off
            )
            if slot_start >= now and not blocked:
                slots.append(slot_start.time())
            current += timedelta(minutes=service.duration_minutes)

    return slots

def get_daily_availability(professional, date_obj, service_duration):
    """
    Retorna os horários disponíveis.
    Calcula a duração do serviço e identifica agendamentos 'encavalados' (pendentes).
    """
    weekday = date_obj.weekday()
    
    # 1. Busca os horários de trabalho da profissional para este dia da semana
    working_hours = WorkingHours.objects.filter(professional=professional, weekday=weekday)
    if not working_hours.exists():
        return []

    # 2. Busca TODOS os agendamentos do dia (do início ao fim)
    start_of_day = timezone.make_aware(datetime.combine(date_obj, time.min))
    end_of_day = timezone.make_aware(datetime.combine(date_obj, time.max))
    
    appointments = Appointment.objects.filter(
        professional=professional,
        start_datetime__lt=end_of_day,
        end_datetime__gt=start_of_day
    )

    # Função interna para classificar cada bloco de horário
    def check_slot_status(slot_start, slot_end):
        slot_status = 'livre'
        
        for appt in appointments:
            # Se houver intersecção (choque) entre o bloco gerado e o agendamento do banco
            if appt.start_datetime < slot_end and appt.end_datetime > slot_start:
                
                # Se for um agendamento já aprovado, o horário tá morto. Ocupado de vez.
                if appt.status == 'confirmado':
                    return 'ocupado'  
                
                # Se for um agendamento na fila, libera o slot, mas com o alerta de encavalamento!
                elif appt.status == 'aguardando_aprovacao':
                    slot_status = 'conflito_pendente'
                    
        return slot_status

    available_slots = []
    
    # 3. Gera os blocos de horário baseados no expediente da profissional
    for wh in working_hours:
        current_time = timezone.make_aware(datetime.combine(date_obj, wh.start_time))
        end_time = timezone.make_aware(datetime.combine(date_obj, wh.end_time))

        # Roda o loop enquanto o serviço couber antes do fim do expediente
        while current_time + timedelta(minutes=service_duration) <= end_time:
            slot_end = current_time + timedelta(minutes=service_duration)
            
            # Bloqueio contra "viagem no tempo" (ignora horários no passado se for o dia de hoje)
            if current_time < timezone.now():
                current_time += timedelta(minutes=30) # Pulo padrão de 30 em 30 min
                continue

            status = check_slot_status(current_time, slot_end)
            
            # O Django SÓ manda pro React o que der pra clicar (livre ou com aviso)
            if status != 'ocupado':
                available_slots.append({
                    "time": current_time.strftime("%H:%M"),
                    "status": status # Devolve 'livre' ou 'conflito_pendente'
                })

            # Avança o relógio para gerar o próximo bloco (ex: de 30 em 30 minutos)
            current_time += timedelta(minutes=30)

    return available_slots