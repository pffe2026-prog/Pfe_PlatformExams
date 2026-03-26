import hashlib
import hmac
from datetime import timedelta
from types import SimpleNamespace

from allauth.core.exceptions import ImmediateHttpResponse
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from gestion.models import Examen, Profil
from .adapters import ExistingUserOnlySocialAccountAdapter
from .forms import ExamenForm
from .views import _google_oauth_configured, _normalize_github_repository


class UIAuthenticationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.password = "TestPass123!"
        self.user = user_model.objects.create_user(
            username="etudiant1",
            email="etudiant1@example.com",
            password=self.password,
        )
        self.login_url = reverse("ui:login")
        self.oauth_login_url = reverse("ui:oauth_email_login")

    @staticmethod
    def _oauth_sig(email, ts, secret):
        payload = f"{email}:{ts}".encode("utf-8")
        return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    def test_login_accepts_email_identifier(self):
        response = self.client.post(
            self.login_url,
            {"username": self.user.email, "password": self.password},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(str(self.user.id), self.client.session.get("_auth_user_id"))

    @override_settings(
        OAUTH_EMAIL_AUTOLOGIN_SECRET="oauth-secret-test",
        OAUTH_EMAIL_MAX_AGE_SECONDS=300,
    )
    def test_oauth_autologin_logs_in_matching_email(self):
        ts = int(timezone.now().timestamp())
        sig = self._oauth_sig(self.user.email, ts, "oauth-secret-test")

        response = self.client.get(
            self.oauth_login_url,
            {"email": self.user.email, "ts": ts, "sig": sig},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(str(self.user.id), self.client.session.get("_auth_user_id"))

    @override_settings(
        OAUTH_EMAIL_AUTOLOGIN_SECRET="oauth-secret-test",
        OAUTH_EMAIL_MAX_AGE_SECONDS=300,
    )
    def test_oauth_autologin_rejects_invalid_signature(self):
        ts = int(timezone.now().timestamp())

        response = self.client.get(
            self.oauth_login_url,
            {"email": self.user.email, "ts": ts, "sig": "invalid"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(self.client.session.get("_auth_user_id"))

    @override_settings(
        OAUTH_EMAIL_AUTOLOGIN_SECRET="oauth-secret-test",
        OAUTH_EMAIL_MAX_AGE_SECONDS=60,
    )
    def test_oauth_autologin_rejects_expired_link(self):
        ts = int(timezone.now().timestamp()) - 3600
        sig = self._oauth_sig(self.user.email, ts, "oauth-secret-test")

        response = self.client.get(
            self.oauth_login_url,
            {"email": self.user.email, "ts": ts, "sig": sig},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(self.client.session.get("_auth_user_id"))


class GitHubRepositoryNormalizationTests(TestCase):
    def test_normalize_https_url(self):
        repo = _normalize_github_repository(
            "https://github.com/karkouri001/exam-java-somme-pairs-tests.git"
        )
        self.assertEqual(repo, "karkouri001/exam-java-somme-pairs-tests")

    def test_normalize_ssh_url(self):
        repo = _normalize_github_repository(
            "git@github.com:karkouri001/exam-java-somme-pairs-tests.git"
        )
        self.assertEqual(repo, "karkouri001/exam-java-somme-pairs-tests")

    def test_keep_owner_repo_value(self):
        repo = _normalize_github_repository("karkouri001/exam-java-somme-pairs-tests")
        self.assertEqual(repo, "karkouri001/exam-java-somme-pairs-tests")


class ExamenFormValidationTests(TestCase):
    def _base_data(self):
        now = timezone.now().replace(second=0, microsecond=0)
        return {
            "titre": "Exam UI",
            "description": "Desc",
            "heure_debut": now.strftime("%Y-%m-%dT%H:%M"),
            "heure_fin": (now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"),
            "groupes_autorises": [],
            "url_tests_git": "",
            "hash_tests": "",
        }

    def test_brouillon_without_pdf_is_valid(self):
        data = self._base_data()
        data["statut"] = "BROUILLON"
        form = ExamenForm(data=data, files={})
        self.assertTrue(form.is_valid(), form.errors)

    def test_non_brouillon_without_pdf_is_invalid(self):
        data = self._base_data()
        data["statut"] = "PUBLIE"
        form = ExamenForm(data=data, files={})
        self.assertFalse(form.is_valid())
        self.assertIn("pdf_examen", form.errors)

    def test_titre_with_html_is_invalid(self):
        data = self._base_data()
        data["titre"] = "<script>alert(1)</script>"
        data["statut"] = "BROUILLON"
        form = ExamenForm(data=data, files={})
        self.assertFalse(form.is_valid())
        self.assertIn("titre", form.errors)


class GoogleOAuthConfiguredTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @staticmethod
    def _request(factory):
        return factory.get("/connexion/")

    @override_settings(
        SOCIALACCOUNT_PROVIDERS={
            "google": {
                "SCOPE": ["profile", "email"],
                "AUTH_PARAMS": {"access_type": "online"},
                "APP": {"client_id": "client-id", "secret": "client-secret", "key": ""},
            }
        }
    )
    def test_google_oauth_configured_via_settings_app(self):
        self.assertTrue(_google_oauth_configured(self._request(self.factory)))

    @override_settings(
        SOCIALACCOUNT_PROVIDERS={
            "google": {
                "SCOPE": ["profile", "email"],
                "AUTH_PARAMS": {"access_type": "online"},
            }
        }
    )
    def test_google_oauth_not_configured_without_socialapp_or_settings_app(self):
        self.assertFalse(_google_oauth_configured(self._request(self.factory)))


class HomeRoutingTests(TestCase):
    def test_home_creates_default_student_profile_when_missing(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username="oauthuser",
            email="oauthuser@example.com",
            password="TestPass123!",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("ui:home"))

        self.assertRedirects(response, reverse("ui:etudiant_dashboard"))
        profil = Profil.objects.get(utilisateur=user)
        self.assertEqual(profil.role, "ETUDIANT")


class ExamenStatusAutoSyncUITests(TestCase):
    def test_teacher_examens_page_synchronizes_exam_status(self):
        user_model = get_user_model()
        enseignant = user_model.objects.create_user(
            username="enseignant_sync",
            email="enseignant_sync@example.com",
            password="TestPass123!",
        )
        Profil.objects.create(utilisateur=enseignant, role="ENSEIGNANT")

        now = timezone.now()
        examen = Examen.objects.create(
            titre="Exam termine",
            description="Desc",
            heure_debut=now - timedelta(hours=2),
            heure_fin=now - timedelta(hours=1),
            statut="PUBLIE",
            cree_par=enseignant,
        )

        self.client.force_login(enseignant)
        response = self.client.get(reverse("ui:enseignant_examens"))

        self.assertEqual(response.status_code, 200)
        examen.refresh_from_db()
        self.assertEqual(examen.statut, "FERME")


class BasicSecurityHeadersTests(TestCase):
    def test_login_page_sets_basic_security_headers(self):
        response = self.client.get(reverse("ui:login"))
        self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(response.headers.get("Referrer-Policy"), "same-origin")
        self.assertEqual(response.headers.get("Cross-Origin-Opener-Policy"), "same-origin")


class ExistingUserOnlySocialAdapterTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.adapter = ExistingUserOnlySocialAccountAdapter()

    def _request(self):
        request = self.factory.get("/accounts/google/login/callback/")
        request.user = AnonymousUser()
        return request

    @staticmethod
    def _sociallogin(email, is_existing=False):
        return SimpleNamespace(
            user=SimpleNamespace(email=email),
            email_addresses=[],
            account=SimpleNamespace(extra_data={"email": email}),
            is_existing=is_existing,
        )

    def test_adapter_blocks_unknown_email(self):
        request = self._request()
        sociallogin = self._sociallogin("inconnu@example.com")
        with self.assertRaises(ImmediateHttpResponse):
            self.adapter.pre_social_login(request, sociallogin)

    def test_adapter_allows_existing_local_email(self):
        user_model = get_user_model()
        user_model.objects.create_user(
            username="compte_local",
            email="connu@example.com",
            password="TestPass123!",
        )
        request = self._request()
        sociallogin = self._sociallogin("connu@example.com")
        self.adapter.pre_social_login(request, sociallogin)

    def test_adapter_allows_existing_social_login(self):
        request = self._request()
        sociallogin = self._sociallogin("quelconque@example.com", is_existing=True)
        self.adapter.pre_social_login(request, sociallogin)
