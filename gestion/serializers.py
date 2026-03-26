from django.utils import timezone
from rest_framework import serializers

from .input_security import clean_plain_text, validate_source_code
from .models import Examen, GroupeAcademique, Resultat, Soumission


class GroupeAcademiqueSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupeAcademique
        fields = "__all__"

    def validate_nom(self, value):
        return clean_plain_text(value, "Le nom du groupe")

    def validate_annee_academique(self, value):
        return clean_plain_text(value, "L annee academique")


class ExamenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Examen
        fields = "__all__"
        read_only_fields = ("cree_par",)

    def validate_titre(self, value):
        return clean_plain_text(value, "Le titre")

    def validate_description(self, value):
        return clean_plain_text(value, "La description")

    def validate(self, attrs):
        instance = self.instance
        statut = attrs.get("statut", getattr(instance, "statut", "BROUILLON"))
        pdf_examen = attrs.get("pdf_examen", getattr(instance, "pdf_examen", None))
        if statut != "BROUILLON" and not pdf_examen:
            raise serializers.ValidationError(
                "Le PDF de l examen est obligatoire hors brouillon."
            )
        if instance and instance.statut != "BROUILLON":
            url_tests_git = attrs.get("url_tests_git", instance.url_tests_git)
            hash_tests = attrs.get("hash_tests", instance.hash_tests)
            if url_tests_git != instance.url_tests_git or hash_tests != instance.hash_tests:
                raise serializers.ValidationError(
                    "Les tests ne peuvent plus etre modifies apres publication."
                )
        return attrs


class SoumissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Soumission
        fields = "__all__"
        read_only_fields = ("trace_id", "soumis_le", "etudiant")

    def validate_code_source(self, value):
        return validate_source_code(value)

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        examen = attrs.get("examen") or getattr(self.instance, "examen", None)
        if not user or not user.is_authenticated:
            raise serializers.ValidationError("Authentification requise.")
        code_source = (attrs.get("code_source") or "").strip()
        url_depot_git = (attrs.get("url_depot_git") or "").strip()
        if not code_source and not url_depot_git:
            raise serializers.ValidationError(
                "Vous devez fournir un code source ou un depot Git."
            )
        if not examen:
            return attrs
        if not examen.groupes_autorises.filter(membres=user).exists():
            raise serializers.ValidationError(
                "Vous n'appartenez a aucun groupe autorise pour cet examen."
            )
        now = timezone.now()
        if now < examen.heure_debut or now > examen.heure_fin:
            raise serializers.ValidationError(
                "La soumission est autorisee uniquement pendant la plage horaire."
            )
        existing = Soumission.objects.filter(examen=examen, etudiant=user)
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise serializers.ValidationError(
                "Vous avez deja soumis pour cet examen."
            )
        return attrs


class ResultatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resultat
        fields = "__all__"
        read_only_fields = ("corrige_le",)

    def validate_feedback(self, value):
        return clean_plain_text(value, "Le commentaire")


class WebhookResultatSerializer(serializers.Serializer):
    soumission = serializers.PrimaryKeyRelatedField(
        queryset=Soumission.objects.all()
    )
    note = serializers.DecimalField(max_digits=5, decimal_places=2)
    feedback = serializers.CharField(allow_blank=True, required=False)
    statut_soumission = serializers.ChoiceField(choices=["CORRIGE", "ECHEC"])

    def validate_feedback(self, value):
        return clean_plain_text(value, "Le commentaire")
