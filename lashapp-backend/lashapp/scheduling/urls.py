from django.urls import path

from scheduling.views import (
    AppointmentApproveView,
    AppointmentCancelView,
    AppointmentListCreateView,
    AppointmentRejectView,
)

app_name = "scheduling"

urlpatterns = [
    path("", AppointmentListCreateView.as_view(), name="appointment-list"),
    path("<int:pk>/", AppointmentCancelView.as_view(), name="appointment-detail"),
    path("<int:pk>/approve/", AppointmentApproveView.as_view(), name="appointment-approve"),
    path("<int:pk>/reject/", AppointmentRejectView.as_view(), name="appointment-reject"),
]
