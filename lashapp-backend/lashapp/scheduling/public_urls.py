from django.urls import path

from scheduling.public_views import (
    AvailabilityView,
    ProfessionalAgendaView,
    PublicAppointmentCreateView,
)

app_name = "scheduling-public"

urlpatterns = [
    path("<slug:slug>/", ProfessionalAgendaView.as_view(), name="agenda-detail"),
    path("<slug:slug>/availability/", AvailabilityView.as_view(), name="agenda-availability"),
    path("<slug:slug>/appointments/", PublicAppointmentCreateView.as_view(), name="public-appointment-create"),
]
