import base64
import binascii
import logging

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db import transaction
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from users.serializers import ClientSerializer, RegisterSerializer, UserSerializer
from users.emailing import VERIFICATION_SALT, send_password_reset_email, send_verification_email

User = get_user_model()
logger = logging.getLogger(__name__)


class AuthEmailThrottle(ScopedRateThrottle):
    scope = "auth_email"


class RegisterView(generics.CreateAPIView):
    """Cadastro público de clientes (necessário para poder agendar)."""

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthEmailThrottle]
    throttle_scope = "auth_email"

    def post(self, request):
        token = request.data.get("token")
        try:
            payload = TimestampSigner(salt=VERIFICATION_SALT).unsign_object(
                token, max_age=24 * 60 * 60
            )
            user = User.objects.get(pk=payload["uid"], email=payload["email"])
        except (TypeError, KeyError, User.DoesNotExist, BadSignature, SignatureExpired):
            return Response(
                {"detail": "Token inválido ou expirado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_email_verified = True
        user.save(update_fields=["is_email_verified", "updated_at"])
        return Response({"detail": "E-mail confirmado com sucesso."})


class ResendVerificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AuthEmailThrottle]
    throttle_scope = "auth_email"

    def post(self, request):
        if request.user.is_email_verified:
            return Response(
                {"detail": "Seu e-mail já foi confirmado."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            send_verification_email(request.user)
        except Exception:
            logger.exception("Falha ao reenviar confirmação para %s", request.user.email)
            return Response(
                {"detail": "Não foi possível enviar o e-mail de confirmação."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"detail": "E-mail de confirmação enviado."})


class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthEmailThrottle]
    throttle_scope = "auth_email"

    def post(self, request):
        email = request.data.get("email", "")
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            try:
                send_password_reset_email(user, default_token_generator.make_token(user))
            except Exception:
                logger.exception("Falha ao enviar recuperação para %s", user.email)
        return Response(
            {"detail": "Se o e-mail estiver cadastrado, enviaremos instruções para redefinir sua senha."}
        )


class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        try:
            uid = base64.urlsafe_b64decode(request.data.get("uid", "")).decode()
            user = User.objects.get(pk=uid, is_active=True)
        except (TypeError, ValueError, UnicodeDecodeError, binascii.Error, User.DoesNotExist):
            return Response(
                {"detail": "Token inválido ou expirado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        token = request.data.get("token", "")
        if not default_token_generator.check_token(user, token):
            return Response(
                {"detail": "Token inválido ou expirado."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            validate_password(request.data.get("password", ""), user)
        except ValidationError as error:
            return Response(
                {"password": error.messages},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            user.set_password(request.data["password"])
            user.save(update_fields=["password", "updated_at"])
            if apps.is_installed("rest_framework_simplejwt.token_blacklist"):
                from rest_framework_simplejwt.token_blacklist.models import (
                    BlacklistedToken,
                    OutstandingToken,
                )

                for outstanding in OutstandingToken.objects.filter(user=user):
                    BlacklistedToken.objects.get_or_create(token=outstanding)
        return Response({"detail": "Senha redefinida com sucesso."})


class MeView(generics.RetrieveUpdateAPIView):
    """Dados da usuária autenticada."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ClientListCreateView(generics.ListCreateAPIView):
    serializer_class = ClientSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        if not self.request.user.is_professional:
            return User.objects.none()
        return User.objects.filter(is_professional=False).order_by("name")

    def perform_create(self, serializer):
        if not self.request.user.is_professional:
            raise permissions.PermissionDenied("Somente profissionais podem cadastrar clientes manuais.")
        serializer.save()
