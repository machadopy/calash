from django.urls import path

from scheduling.public_views import (
    AvailabilityView,
    PublicWorkingHoursView,
    PublicScheduleView,
    ProfessionalAgendaView,
    PublicAppointmentCreateView,
    SupportContactView,
)

app_name = "scheduling-public"

urlpatterns = [
    path("support/", SupportContactView.as_view(), name="support-contact"),
    path("<slug:slug>/", ProfessionalAgendaView.as_view(), name="agenda-detail"),
    path("<slug:slug>/availability/", AvailabilityView.as_view(), name="agenda-availability"),
    path("<slug:slug>/working-hours/", PublicWorkingHoursView.as_view(), name="agenda-working-hours"),
    path("<slug:slug>/schedule/", PublicScheduleView.as_view(), name="agenda-schedule"),
    path("<slug:slug>/appointments/", PublicAppointmentCreateView.as_view(), name="public-appointment-create"),
]
