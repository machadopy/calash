from rest_framework import generics, permissions
from django.contrib.auth import get_user_model

from users.serializers import ClientSerializer, RegisterSerializer, UserSerializer

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """Cadastro público de clientes (necessário para poder agendar)."""

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


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
