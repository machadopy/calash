from django.urls import path

from anamnesis.views import AnamnesisListCreateView, AnamnesisPrefillView, download_anamnesis_pdf

app_name = "anamnesis"

urlpatterns = [
    path("", AnamnesisListCreateView.as_view(), name="list-create"),
    path("prefill/", AnamnesisPrefillView.as_view(), name="prefill"),
    path("<int:pk>/pdf/", download_anamnesis_pdf, name="pdf"),
]