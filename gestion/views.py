from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Examen, GroupeAcademique, Resultat, Soumission
from .permissions import IsEnseignantOrAdmin, IsResultatEditor
from .serializers import (
    ExamenSerializer,
    GroupeAcademiqueSerializer,
    ResultatSerializer,
    SoumissionSerializer,
    WebhookResultatSerializer,
)


class GroupeAcademiqueViewSet(viewsets.ModelViewSet):
    queryset = GroupeAcademique.objects.all()
    serializer_class = GroupeAcademiqueSerializer


class ExamenViewSet(viewsets.ModelViewSet):
    queryset = Examen.objects.all()
    serializer_class = ExamenSerializer
    permission_classes = [IsAuthenticated, IsEnseignantOrAdmin]

    def get_queryset(self):
        queryset = super().get_queryset()
        Examen.synchroniser_statuts_automatiques(queryset=queryset)
        profil = getattr(self.request.user, "profil", None)
        if profil and profil.role == "ETUDIANT":
            return queryset.filter(
                groupes_autorises__membres=self.request.user,
                statut__in=["PUBLIE", "EN_COURS"],
            ).distinct()
        return queryset

    def perform_create(self, serializer):
        serializer.save(cree_par=self.request.user)


class SoumissionViewSet(viewsets.ModelViewSet):
    queryset = Soumission.objects.all()
    serializer_class = SoumissionSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(etudiant=self.request.user)


class ResultatViewSet(viewsets.ModelViewSet):
    queryset = Resultat.objects.all()
    serializer_class = ResultatSerializer
    permission_classes = [IsAuthenticated, IsResultatEditor]


class ResultatWebhookAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.headers.get("X-API-TOKEN")
        if token != settings.API_WEBHOOK_TOKEN:
            return Response({"detail": "Token invalide."}, status=status.HTTP_403_FORBIDDEN)
        serializer = WebhookResultatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        soumission = serializer.validated_data["soumission"]
        resultat, created = Resultat.objects.update_or_create(
            soumission=soumission,
            defaults={
                "note": serializer.validated_data["note"],
                "feedback": serializer.validated_data.get("feedback", ""),
            },
        )
        soumission.statut = serializer.validated_data["statut_soumission"]
        soumission.save(update_fields=["statut"])
        return Response(
            {
                "resultat_id": resultat.id,
                "soumission": soumission.id,
                "statut": soumission.statut,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
