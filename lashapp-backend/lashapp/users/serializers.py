from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils.crypto import get_random_string
from rest_framework import serializers

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
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    professional_slug = serializers.CharField(
        source="professional_profile.slug", read_only=True, allow_null=True
    )

    class Meta:
        model = User
        fields = ["id", "email", "name", "phone", "is_professional", "is_superuser", "professional_slug"]
        read_only_fields = ["id", "is_professional", "is_superuser"]
