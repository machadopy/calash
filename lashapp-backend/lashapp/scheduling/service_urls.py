from django.urls import path

from scheduling.views import ServiceListCreateView

app_name = "services"

urlpatterns = [
    path("", ServiceListCreateView.as_view(), name="service-list-create"),
]