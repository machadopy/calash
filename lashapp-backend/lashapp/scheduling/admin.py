from django.contrib import admin

from scheduling.models import Appointment, Service, TimeOff, WorkingHours


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ["name", "professional", "duration_minutes", "price", "is_active"]
    list_filter = ["professional", "is_active"]


@admin.register(WorkingHours)
class WorkingHoursAdmin(admin.ModelAdmin):
    list_display = ["professional", "weekday", "start_time", "end_time"]
    list_filter = ["professional", "weekday"]


@admin.register(TimeOff)
class TimeOffAdmin(admin.ModelAdmin):
    list_display = ["professional", "start_datetime", "end_datetime", "reason"]


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ["client", "professional", "service", "start_datetime", "status"]
    list_filter = ["status", "professional"]
    search_fields = ["client__name", "client__email"]
