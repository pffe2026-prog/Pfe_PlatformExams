import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Profil(models.Model):
    ROLE_CHOICES = [
        ("ETUDIANT", "Etudiant"),
        ("ENSEIGNANT", "Enseignant"),
        ("ADMIN", "Admin"),
    ]

    utilisateur = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profil"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    class Meta:
        db_table = "Profil"

    def __str__(self) -> str:
        return f"{self.utilisateur.username} ({self.role})"


class GroupeAcademique(models.Model):
    nom = models.CharField(max_length=200)
    annee_academique = models.CharField(max_length=20)
    membres = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="groupes_academiques", blank=True
    )

    class Meta:
        db_table = "GroupeAcademique"

    def __str__(self) -> str:
        return f"{self.nom} - {self.annee_academique}"


class Examen(models.Model):
    STATUT_CHOICES = [
        ("BROUILLON", "Brouillon"),
        ("PUBLIE", "Publie"),
        ("EN_COURS", "En cours"),
        ("FERME", "Ferme"),
    ]

    titre = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    heure_debut = models.DateTimeField()
    heure_fin = models.DateTimeField()
    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES, default="BROUILLON"
    )
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="examens_crees"
    )
    url_tests_git = models.URLField(blank=True, null=True)
    hash_tests = models.CharField(max_length=40, blank=True)
    pdf_examen = models.FileField(
        upload_to="examens/pdfs/",
        blank=True,
        null=True,
    )
    groupes_autorises = models.ManyToManyField(
        GroupeAcademique, related_name="examens", blank=True
    )

    class Meta:
        db_table = "Examen"

    def __str__(self) -> str:
        return self.titre

    def statut_attendu(self, now=None) -> str:
        if self.statut == "BROUILLON":
            return "BROUILLON"

        current_time = now or timezone.now()
        if current_time < self.heure_debut:
            return "PUBLIE"
        if current_time <= self.heure_fin:
            return "EN_COURS"
        return "FERME"

    def synchroniser_statut(self, now=None, save=True) -> str:
        statut_cible = self.statut_attendu(now=now)
        if statut_cible != self.statut:
            self.statut = statut_cible
            if save and self.pk:
                self.save(update_fields=["statut"])
        return self.statut

    @classmethod
    def synchroniser_statuts_automatiques(cls, now=None, queryset=None) -> int:
        current_time = now or timezone.now()
        base_queryset = (queryset or cls.objects.all()).exclude(statut="BROUILLON")
        updated = 0
        updated += base_queryset.filter(heure_debut__gt=current_time).exclude(
            statut="PUBLIE"
        ).update(statut="PUBLIE")
        updated += base_queryset.filter(
            heure_debut__lte=current_time,
            heure_fin__gte=current_time,
        ).exclude(statut="EN_COURS").update(statut="EN_COURS")
        updated += base_queryset.filter(heure_fin__lt=current_time).exclude(
            statut="FERME"
        ).update(statut="FERME")
        return updated


class Soumission(models.Model):
    STATUT_CHOICES = [
        ("EN_ATTENTE", "En attente"),
        ("EN_TEST", "En test"),
        ("CORRIGE", "Corrige"),
        ("ECHEC", "Echec"),
    ]

    trace_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    examen = models.ForeignKey(Examen, on_delete=models.CASCADE, related_name="soumissions")
    etudiant = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="soumissions"
    )
    url_depot_git = models.URLField(max_length=500, blank=True, null=True)
    hash_commit = models.CharField(max_length=100, blank=True)
    code_source = models.TextField(blank=True)
    soumis_le = models.DateTimeField(auto_now_add=True)
    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES, default="EN_ATTENTE"
    )

    class Meta:
        db_table = "Soumission"
        constraints = [
            models.UniqueConstraint(
                fields=["examen", "etudiant"],
                name="unique_soumission_par_etudiant",
            )
        ]

    def __str__(self) -> str:
        return f"{self.examen.titre} - {self.etudiant.username}"


class Resultat(models.Model):
    soumission = models.OneToOneField(
        Soumission, on_delete=models.CASCADE, related_name="resultat"
    )
    note = models.DecimalField(max_digits=5, decimal_places=2)
    feedback = models.TextField(blank=True)
    corrige_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "Resultat"

    def __str__(self) -> str:
        return f"Resultat {self.soumission.trace_id}"


class JournalAudit(models.Model):
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="actions_audit",
    )
    action = models.CharField(max_length=255)
    horodatage = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "JournalAudit"

    def __str__(self) -> str:
        return f"{self.horodatage} - {self.action}"
