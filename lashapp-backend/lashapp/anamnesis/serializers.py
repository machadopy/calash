import base64
import binascii
import io
import uuid

from PIL import Image
from django.core.files.base import ContentFile
from django.utils import timezone
from rest_framework import serializers

from anamnesis.models import Anamnesis


SIGNATURE_MAX_BYTES = 500 * 1024


class AnamnesisSerializer(serializers.ModelSerializer):
    signature = serializers.CharField(write_only=True)

    class Meta:
        model = Anamnesis
        fields = [
            "id", "appointment", "client", "professional", "full_name", "birth_date", "whatsapp",
            "instagram", "profession", "how_met", "had_previous_extension",
            "had_previous_extension_notes", "has_allergies", "has_allergies_notes",
            "uses_contact_lenses", "uses_contact_lenses_notes", "has_eye_problems",
            "has_eye_problems_notes", "recent_eye_procedure", "recent_eye_procedure_notes",
            "thyroid_alopecia_hormonal", "thyroid_alopecia_hormonal_notes",
            "pregnant_or_treatment", "pregnant_or_treatment_notes",
            "pulls_lashes_or_sleeps_prone", "pulls_lashes_or_sleeps_prone_notes",
            "consent_accepted", "signed_date", "signature", "procedure_date", "technique",
            "curvature", "thickness", "adhesive", "mapping", "pdf", "created_at",
        ]
        read_only_fields = [
            "appointment", "client", "professional", "procedure_date", "technique",
            "curvature", "thickness", "adhesive", "mapping", "pdf", "created_at",
        ]

    def validate_signature(self, value):
        if not isinstance(value, str) or not value.startswith("data:image/png;base64,"):
            raise serializers.ValidationError("A assinatura deve ser uma imagem PNG em data URL.")

        encoded = value.partition(",")[2]
        try:
            decoded = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error):
            raise serializers.ValidationError("A assinatura PNG é inválida.")

        if len(decoded) > SIGNATURE_MAX_BYTES:
            raise serializers.ValidationError("A assinatura não pode ultrapassar 500 KB.")

        try:
            with Image.open(io.BytesIO(decoded)) as image:
                if image.format != "PNG":
                    raise ValueError
                rgba = image.convert("RGBA")
                visible = [pixel for pixel in rgba.getdata() if pixel[3] > 16]
                if len(visible) < 20:
                    raise ValueError
                non_white = [pixel for pixel in visible if min(pixel[:3]) < 220]
                if len(non_white) < 12:
                    raise ValueError
        except (OSError, ValueError):
            raise serializers.ValidationError("A assinatura não pode estar em branco.")

        return ContentFile(decoded, name=f"signature-{uuid.uuid4().hex}.png")

    def validate(self, attrs):
        if not attrs.get("consent_accepted"):
            raise serializers.ValidationError({"consent_accepted": "O consentimento é obrigatório."})
        if attrs.get("signed_date") != timezone.localdate():
            raise serializers.ValidationError({"signed_date": "A data deve ser a data de hoje."})
        return attrs


class AnamnesisPrefillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Anamnesis
        fields = [
            "full_name", "birth_date", "whatsapp", "instagram", "profession", "how_met",
            "had_previous_extension", "had_previous_extension_notes", "has_allergies",
            "has_allergies_notes", "uses_contact_lenses", "uses_contact_lenses_notes",
            "has_eye_problems", "has_eye_problems_notes", "recent_eye_procedure",
            "recent_eye_procedure_notes", "thyroid_alopecia_hormonal",
            "thyroid_alopecia_hormonal_notes", "pregnant_or_treatment",
            "pregnant_or_treatment_notes", "pulls_lashes_or_sleeps_prone",
            "pulls_lashes_or_sleeps_prone_notes", "signed_date", "signature",
            "consent_accepted",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["signed_date"] = ""
        data["signature"] = ""
        data["consent_accepted"] = False
        return data