import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from users.emailing import send_verification_email

logger = logging.getLogger(__name__)

User = get_user_model()


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "name", "phone"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        return User.objects.create_user(
            password=get_random_string(32),
            **validated_data,
        )


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["id", "email", "password", "name", "phone"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        try:
            send_verification_email(user)
        except Exception:
            logger.exception("Falha ao enviar confirmação de e-mail para %s", user.email)
        return user


class UserSerializer(serializers.ModelSerializer):
    professional_slug = serializers.CharField(
        source="professional_profile.slug", read_only=True, allow_null=True
    )

    class Meta:
        model = User
        fields = [
            "id", "email", "name", "phone", "is_professional", "is_superuser",
            "is_email_verified", "professional_slug",
        ]
        read_only_fields = ["id", "is_professional", "is_superuser"]
