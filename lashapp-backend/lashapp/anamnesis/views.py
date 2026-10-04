from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from anamnesis.models import Anamnesis
from anamnesis.serializers import AnamnesisPrefillSerializer, AnamnesisSerializer
from professionals.models import Professional


def profissional_da_requisicao(request):
    if request.user.is_superuser and not request.user.is_professional:
        return Professional.objects.first()
    return request.user.professional_profile


class IsProfessionalOrStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user.is_authenticated
            and (request.user.is_superuser or request.user.is_professional)
        )


class AnamnesisListCreateView(APIView):
    permission_classes = [IsProfessionalOrStaff]

    def get(self, request):
        queryset = Anamnesis.objects.filter(professional=profissional_da_requisicao(request))
        selected_date = request.query_params.get("date")
        if selected_date:
            queryset = queryset.filter(
                Q(procedure_date=selected_date) | Q(procedure_date__isnull=True, signed_date=selected_date)
            )
        return Response(AnamnesisSerializer(queryset, many=True).data)

    def post(self, request):
        client_id = request.data.get("client")
        if not client_id:
            return Response({"client": ["Selecione uma cliente."]}, status=400)

        client = get_object_or_404(get_user_model(), pk=client_id, is_professional=False)
        payload = request.data.copy()
        payload.pop("client", None)
        procedure_date = payload.pop("date", None)
        if procedure_date:
            payload["procedure_date"] = procedure_date

        serializer = AnamnesisSerializer(data=payload, context={"request": request})
        serializer.is_valid(raise_exception=True)
        anamnesis = serializer.save(
            client=client,
            professional=profissional_da_requisicao(request),
        )
        if procedure_date:
            anamnesis.procedure_date = procedure_date
            anamnesis.save(update_fields=["procedure_date"])
        from anamnesis.services import generate_anamnesis_pdf_safely
        generate_anamnesis_pdf_safely(anamnesis)
        return Response(AnamnesisSerializer(anamnesis).data, status=201)


class AnamnesisPrefillView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        client_id = request.query_params.get("client_id")
        if request.user.is_professional or request.user.is_superuser:
            if not client_id:
                return Response(status=204)
            anamnesis = Anamnesis.objects.filter(
                client_id=client_id,
                professional=profissional_da_requisicao(request),
            ).first()
        else:
            anamnesis = Anamnesis.objects.filter(client=request.user).first()
        if not anamnesis:
            return Response(status=204)
        return Response(AnamnesisPrefillSerializer(anamnesis).data)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def download_anamnesis_pdf(request, pk):
    anamnesis = get_object_or_404(Anamnesis, pk=pk)
    is_owner = (
        request.user.is_professional
        and anamnesis.professional.user_id == request.user.id
    )
    if not (request.user.is_staff or is_owner):
        raise PermissionDenied("Você não tem permissão para acessar esta ficha.")
    if not anamnesis.pdf:
        from anamnesis.services import generate_anamnesis_pdf_safely
        generate_anamnesis_pdf_safely(anamnesis)
        anamnesis.refresh_from_db()
    if not anamnesis.pdf:
        raise Http404("O PDF desta ficha ainda não foi gerado.")
    response = FileResponse(
        anamnesis.pdf.open("rb"),
        as_attachment=True,
        filename=f"anamnesis-{anamnesis.pk}.pdf",
        content_type="application/pdf",
    )
    response["Content-Disposition"] = f'attachment; filename="anamnesis-{anamnesis.pk}.pdf"'
    return response