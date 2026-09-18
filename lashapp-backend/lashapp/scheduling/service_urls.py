from django.urls import path

from scheduling.views import LunchBreakView, ServiceDetailView, ServiceListCreateView, WorkingHoursView

app_name = "services"

urlpatterns = [
    path("working-hours/", WorkingHoursView.as_view(), name="working-hours"),
    path("lunch-breaks/", LunchBreakView.as_view(), name="lunch-breaks"),
    path("<int:pk>/", ServiceDetailView.as_view(), name="service-detail"),
    path("", ServiceListCreateView.as_view(), name="service-list-create"),
]