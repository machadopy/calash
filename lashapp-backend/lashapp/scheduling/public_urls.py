from django.urls import path

from scheduling.public_views import AvailabilityView, ProfessionalAgendaView

app_name = "scheduling-public"

urlpatterns = [
    path("<slug:slug>/", ProfessionalAgendaView.as_view(), name="agenda-detail"),
    path("<slug:slug>/availability/", AvailabilityView.as_view(), name="agenda-availability"),
]
