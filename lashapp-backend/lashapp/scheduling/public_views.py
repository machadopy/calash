from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from professionals.models import Professional
from scheduling.availability import get_available_slots
from scheduling.models import Service
from scheduling.serializers import AvailabilityQuerySerializer, ProfessionalPublicSerializer


class ProfessionalAgendaView(generics.RetrieveAPIView):
    """Perfil público da profissional + lista de serviços. Não exige login."""

    serializer_class = ProfessionalPublicSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"
    queryset = Professional.objects.filter(is_active=True)


class AvailabilityView(APIView):
    """Horários livres para um serviço numa data. Não exige login."""

    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        professional = get_object_or_404(Professional, slug=slug, is_active=True)

        query = AvailabilityQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        service = get_object_or_404(
            Service, id=query.validated_data["service_id"], professional=professional
        )

        slots = get_available_slots(professional, service, query.validated_data["date"])

        return Response({"slots": [s.strftime("%H:%M") for s in slots]})
