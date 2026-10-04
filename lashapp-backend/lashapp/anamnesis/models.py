from django.conf import settings
from django.db import models

from anamnesis.storage import private_storage


class Anamnesis(models.Model):
    class Technique(models.TextChoices):
        FIO_A_FIO = "fio_a_fio", "Fio a Fio"
        VOLUME_RUSSO = "volume_russo", "Vol. Russo"
        HIBRIDO = "hibrido", "Híbrido"

    class Mapping(models.TextChoices):
        GATINHO = "gatinho", "Gatinho"
        BONECA = "boneca", "Boneca"
        ESQUILO = "esquilo", "Esquilo"

    appointment = models.OneToOneField(
        "scheduling.Appointment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="anamnesis",
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL,  # <-- Alterado para não apagar a ficha quando o user for deletado
        null=True,                  # <-- Permite valor nulo no banco
        blank=True,                 # <-- Permite ficar em branco em formulários
        related_name="anamneses"
    )
    professional = models.ForeignKey(
        "professionals.Professional", on_delete=models.CASCADE, related_name="anamneses"
    )

    full_name = models.CharField(max_length=150)
    birth_date = models.DateField()
    whatsapp = models.CharField(max_length=30, blank=True)
    instagram = models.CharField(max_length=100, blank=True)
    profession = models.CharField(max_length=100, blank=True)
    how_met = models.CharField(max_length=150, blank=True)

    had_previous_extension = models.BooleanField()
    had_previous_extension_notes = models.TextField(max_length=500, blank=True)
    has_allergies = models.BooleanField()
    has_allergies_notes = models.TextField(max_length=500, blank=True)
    uses_contact_lenses = models.BooleanField()
    uses_contact_lenses_notes = models.TextField(max_length=500, blank=True)
    has_eye_problems = models.BooleanField()
    has_eye_problems_notes = models.TextField(max_length=500, blank=True)
    recent_eye_procedure = models.BooleanField()
    recent_eye_procedure_notes = models.TextField(max_length=500, blank=True)
    thyroid_alopecia_hormonal = models.BooleanField()
    thyroid_alopecia_hormonal_notes = models.TextField(max_length=500, blank=True)
    pregnant_or_treatment = models.BooleanField()
    pregnant_or_treatment_notes = models.TextField(max_length=500, blank=True)
    pulls_lashes_or_sleeps_prone = models.BooleanField()
    pulls_lashes_or_sleeps_prone_notes = models.TextField(max_length=500, blank=True)

    consent_accepted = models.BooleanField(default=False)
    signed_date = models.DateField()
    signature = models.ImageField(upload_to="signatures/%Y/%m/", storage=private_storage)

    procedure_date = models.DateField(null=True, blank=True)
    technique = models.CharField(max_length=20, choices=Technique.choices, blank=True)
    curvature = models.CharField(max_length=20, blank=True)
    thickness = models.CharField(max_length=20, blank=True)
    adhesive = models.CharField(max_length=100, blank=True)
    mapping = models.CharField(max_length=20, choices=Mapping.choices, blank=True)

    pdf = models.FileField(upload_to="pdfs/%Y/%m/", storage=private_storage, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "ficha de anamnese"
        verbose_name_plural = "fichas de anamnese"

    def __str__(self):
        return f"{self.full_name} - {self.created_at:%d/%m/%Y}"