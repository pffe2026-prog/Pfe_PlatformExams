from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import Examen, Profil, Resultat, Soumission


class BaseAPITestCase(APITestCase):
    def create_user_with_role(self, username, role):
        user = get_user_model().objects.create_user(
            username=username, password="pass1234"
        )
        Profil.objects.create(utilisateur=user, role=role)
        return user


class ExamenPermissionsTests(BaseAPITestCase):
    def setUp(self):
        self.etudiant = self.create_user_with_role("etu1", "ETUDIANT")
        self.enseignant = self.create_user_with_role("ens1", "ENSEIGNANT")

    def test_etudiant_ne_peut_pas_post_examens(self):
        self.client.force_authenticate(user=self.etudiant)
        now = timezone.now()
        response = self.client.post(
            "/api/examens/",
            {
                "titre": "Test",
                "description": "Desc",
                "heure_debut": (now - timedelta(hours=1)).isoformat(),
                "heure_fin": (now + timedelta(hours=1)).isoformat(),
                "statut": "BROUILLON",
                "cree_par": self.enseignant.id,
                "groupes_autorises": [],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_cree_par_force_par_request_user(self):
        other_user = self.create_user_with_role("autre", "ENSEIGNANT")
        self.client.force_authenticate(user=self.enseignant)
        now = timezone.now()
        response = self.client.post(
            "/api/examens/",
            {
                "titre": "Exam 1",
                "description": "Desc",
                "heure_debut": (now - timedelta(hours=1)).isoformat(),
                "heure_fin": (now + timedelta(hours=1)).isoformat(),
                "statut": "BROUILLON",
                "cree_par": other_user.id,
                "groupes_autorises": [],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        examen = Examen.objects.get(id=response.data["id"])
        self.assertEqual(examen.cree_par, self.enseignant)

    def test_examen_non_brouillon_exige_pdf(self):
        self.client.force_authenticate(user=self.enseignant)
        now = timezone.now()
        response = self.client.post(
            "/api/examens/",
            {
                "titre": "Exam sans PDF",
                "description": "Desc",
                "heure_debut": (now - timedelta(hours=1)).isoformat(),
                "heure_fin": (now + timedelta(hours=1)).isoformat(),
                "statut": "PUBLIE",
                "groupes_autorises": [],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_examen_rejette_titre_html(self):
        self.client.force_authenticate(user=self.enseignant)
        now = timezone.now()
        response = self.client.post(
            "/api/examens/",
            {
                "titre": "<script>alert(1)</script>",
                "description": "Desc",
                "heure_debut": (now - timedelta(hours=1)).isoformat(),
                "heure_fin": (now + timedelta(hours=1)).isoformat(),
                "statut": "BROUILLON",
                "groupes_autorises": [],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("titre", response.data)


class ExamenStatusSynchronizationTests(BaseAPITestCase):
    def setUp(self):
        self.enseignant = self.create_user_with_role("ens_sync", "ENSEIGNANT")

    def test_sync_time_based_status_moves_published_exam_to_in_progress(self):
        now = timezone.now()
        examen = Examen.objects.create(
            titre="Exam sync",
            description="Desc",
            heure_debut=now - timedelta(minutes=30),
            heure_fin=now + timedelta(minutes=30),
            statut="PUBLIE",
            cree_par=self.enseignant,
        )

        Examen.synchroniser_statuts_automatiques(now=now)

        examen.refresh_from_db()
        self.assertEqual(examen.statut, "EN_COURS")

    def test_sync_time_based_status_keeps_brouillon_unchanged(self):
        now = timezone.now()
        examen = Examen.objects.create(
            titre="Exam draft",
            description="Desc",
            heure_debut=now - timedelta(days=1),
            heure_fin=now - timedelta(hours=1),
            statut="BROUILLON",
            cree_par=self.enseignant,
        )

        Examen.synchroniser_statuts_automatiques(now=now)

        examen.refresh_from_db()
        self.assertEqual(examen.statut, "BROUILLON")

    def test_api_examens_get_synchronizes_status_before_listing(self):
        now = timezone.now()
        examen = Examen.objects.create(
            titre="Exam closed",
            description="Desc",
            heure_debut=now - timedelta(hours=2),
            heure_fin=now - timedelta(hours=1),
            statut="PUBLIE",
            cree_par=self.enseignant,
        )

        self.client.force_authenticate(user=self.enseignant)
        response = self.client.get("/api/examens/")

        self.assertEqual(response.status_code, 200)
        examen.refresh_from_db()
        self.assertEqual(examen.statut, "FERME")


class ResultatWebhookTests(BaseAPITestCase):
    def setUp(self):
        self.etudiant = self.create_user_with_role("etu2", "ETUDIANT")
        self.enseignant = self.create_user_with_role("ens2", "ENSEIGNANT")
        now = timezone.now()
        self.examen = Examen.objects.create(
            titre="Exam webhook",
            description="Desc",
            heure_debut=now - timedelta(hours=1),
            heure_fin=now + timedelta(hours=1),
            statut="PUBLIE",
            cree_par=self.enseignant,
        )
        self.soumission = Soumission.objects.create(
            examen=self.examen,
            etudiant=self.etudiant,
            url_depot_git="https://example.com/repo.git",
            hash_commit="abc123",
        )

    def test_etudiant_ne_peut_pas_post_resultats_ni_webhook_sans_token(self):
        self.client.force_authenticate(user=self.etudiant)
        response = self.client.post(
            "/api/resultats/",
            {"soumission": self.soumission.id, "note": "12.00", "feedback": "OK"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

        webhook_response = self.client.post(
            "/api/webhook/resultats/",
            {
                "soumission": self.soumission.id,
                "note": "14.50",
                "feedback": "OK",
                "statut_soumission": "CORRIGE",
            },
            format="json",
        )
        self.assertEqual(webhook_response.status_code, 403)

    @override_settings(API_WEBHOOK_TOKEN="test-token")
    def test_webhook_avec_bon_token_cree_resultat_et_met_a_jour_soumission(self):
        response = self.client.post(
            "/api/webhook/resultats/",
            {
                "soumission": self.soumission.id,
                "note": "14.50",
                "feedback": "OK",
                "statut_soumission": "CORRIGE",
            },
            format="json",
            HTTP_X_API_TOKEN="test-token",
        )
        self.assertIn(response.status_code, [200, 201])
        self.soumission.refresh_from_db()
        self.assertEqual(self.soumission.statut, "CORRIGE")
        self.assertTrue(Resultat.objects.filter(soumission=self.soumission).exists())

    @override_settings(API_WEBHOOK_TOKEN="test-token")
    def test_webhook_rejette_feedback_html(self):
        response = self.client.post(
            "/api/webhook/resultats/",
            {
                "soumission": self.soumission.id,
                "note": "14.50",
                "feedback": "<img src=x onerror=alert(1)>",
                "statut_soumission": "CORRIGE",
            },
            format="json",
            HTTP_X_API_TOKEN="test-token",
        )
        self.assertEqual(response.status_code, 400)


class SearchInputSanitizationTests(BaseAPITestCase):
    def setUp(self):
        self.etudiant = self.create_user_with_role("etu_search", "ETUDIANT")
        self.enseignant = self.create_user_with_role("ens_search", "ENSEIGNANT")
        now = timezone.now()
        self.examen = Examen.objects.create(
            titre="Algo 1",
            description="Desc",
            heure_debut=now - timedelta(hours=1),
            heure_fin=now + timedelta(hours=1),
            statut="PUBLIE",
            cree_par=self.enseignant,
        )

    def test_teacher_examens_search_ignores_html_input(self):
        self.client.force_login(self.enseignant)
        response = self.client.get("/enseignant/examens/", {"q": "<script>alert(1)</script>"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["q"], "")
