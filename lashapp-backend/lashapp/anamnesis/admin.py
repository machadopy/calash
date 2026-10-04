from django.contrib import admin
from django.urls import path, reverse
from django.utils.html import format_html

from anamnesis.models import Anamnesis
from anamnesis.services import generate_anamnesis_pdf_safely
from anamnesis.views import download_anamnesis_pdf


@admin.register(Anamnesis)
class AnamnesisAdmin(admin.ModelAdmin):
    list_display = ["client", "professional", "procedure_or_appointment_date", "pdf_link"]
    search_fields = ["client__name", "client__email", "full_name"]
    list_filter = ["professional"]
    readonly_fields = [
        "appointment", "client", "professional", "full_name", "birth_date", "whatsapp",
        "instagram", "profession", "how_met", "had_previous_extension",
        "had_previous_extension_notes", "has_allergies", "has_allergies_notes",
        "uses_contact_lenses", "uses_contact_lenses_notes", "has_eye_problems",
        "has_eye_problems_notes", "recent_eye_procedure", "recent_eye_procedure_notes",
        "thyroid_alopecia_hormonal", "thyroid_alopecia_hormonal_notes",
        "pregnant_or_treatment", "pregnant_or_treatment_notes",
        "pulls_lashes_or_sleeps_prone", "pulls_lashes_or_sleeps_prone_notes",
        "consent_accepted", "signed_date", "signature", "pdf", "created_at", "pdf_link",
    ]
    fields = [
        "appointment", "client", "professional", "full_name", "birth_date", "whatsapp",
        "instagram", "profession", "how_met", "had_previous_extension",
        "had_previous_extension_notes", "has_allergies", "has_allergies_notes",
        "uses_contact_lenses", "uses_contact_lenses_notes", "has_eye_problems",
        "has_eye_problems_notes", "recent_eye_procedure", "recent_eye_procedure_notes",
        "thyroid_alopecia_hormonal", "thyroid_alopecia_hormonal_notes",
        "pregnant_or_treatment", "pregnant_or_treatment_notes",
        "pulls_lashes_or_sleeps_prone", "pulls_lashes_or_sleeps_prone_notes",
        "consent_accepted", "signed_date", "signature", "procedure_date", "technique",
        "curvature", "thickness", "adhesive", "mapping", "pdf", "pdf_link", "created_at",
    ]

    def procedure_or_appointment_date(self, obj):
        return obj.procedure_date or (obj.appointment.start_datetime.date() if obj.appointment else "-")

    procedure_or_appointment_date.short_description = "Data do procedimento/agendamento"

    def pdf_link(self, obj):
        if not obj.pdf:
            return "-"
        url = reverse("admin:anamnesis_anamnesis_pdf", args=[obj.pk])
        return format_html('<a href="{}">Baixar PDF</a>', url)

    pdf_link.short_description = "PDF"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("<path:object_id>/pdf/", self.admin_site.admin_view(self.download_pdf), name="anamnesis_anamnesis_pdf"),
        ]
        return custom_urls + urls

    def download_pdf(self, request, object_id):
        return download_anamnesis_pdf(request, object_id)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        generate_anamnesis_pdf_safely(obj)

    def has_delete_permission(self, request, obj=None):
        return False