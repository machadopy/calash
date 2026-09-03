from django.urls import path

from scheduling.views import AppointmentCancelView, AppointmentListCreateView

app_name = "scheduling"

urlpatterns = [
    path("", AppointmentListCreateView.as_view(), name="appointment-list"),
    path("<int:pk>/", AppointmentCancelView.as_view(), name="appointment-detail"),
]
