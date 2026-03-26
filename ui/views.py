import base64
import hashlib
import hmac
import json
from functools import wraps
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings

from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib.sites.shortcuts import get_current_site
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View

from gestion.input_security import clean_digit_filter, clean_search_term
from gestion.models import Examen, Profil, Resultat, Soumission
from gestion.serializers import SoumissionSerializer
from .forms import EmailOrUsernameAuthenticationForm, ExamenForm


def _synchroniser_statuts_examens(queryset=None):
    Examen.synchroniser_statuts_automatiques(queryset=queryset)


def _google_oauth_configured(request) -> bool:
    provider_cfg = getattr(settings, "SOCIALACCOUNT_PROVIDERS", {}).get("google", {})
    app_cfg = provider_cfg.get("APP", {}) if isinstance(provider_cfg, dict) else {}
    configured_via_settings = bool(app_cfg.get("client_id") and app_cfg.get("secret"))

    try:
        from allauth.socialaccount.models import SocialApp

        current_site = get_current_site(request)
        configured_via_socialapp = SocialApp.objects.filter(
            provider="google", sites=current_site
        ).exists()
        return configured_via_socialapp or configured_via_settings
    except Exception:
        return configured_via_settings


def _role(user) -> str:
    profil = getattr(user, "profil", None)
    return getattr(profil, "role", "")


def _enseignant_examens_queryset(user):
    if _role(user) == "ADMIN":
        queryset = Examen.objects.all()
    else:
        queryset = Examen.objects.filter(cree_par=user)
    _synchroniser_statuts_examens(queryset=queryset)
    return queryset


def role_required(*roles):
    def deco(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if _role(request.user) not in roles:
                messages.error(request, "Acces refuse (role insuffisant).")
                return redirect("ui:home")
            return view_func(request, *args, **kwargs)

        return _wrapped

    return deco


def _safe_next_url(request, next_url):
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return settings.LOGIN_REDIRECT_URL


def _oauth_signature_is_valid(email, timestamp, signature):
    secret = getattr(settings, "OAUTH_EMAIL_AUTOLOGIN_SECRET", "")
    if not secret:
        return False, "Configuration OAuth manquante (OAUTH_EMAIL_AUTOLOGIN_SECRET)."

    try:
        issued_at = int(timestamp)
    except (TypeError, ValueError):
        return False, "Parametre ts invalide."

    max_age = int(getattr(settings, "OAUTH_EMAIL_MAX_AGE_SECONDS", 300))
    now = int(timezone.now().timestamp())
    if abs(now - issued_at) > max_age:
        return False, "Lien OAuth expire."

    payload = f"{email}:{issued_at}".encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, (signature or "").strip().lower()):
        return False, "Signature OAuth invalide."

    return True, ""


class EmailLoginView(LoginView):
    template_name = "ui/login.html"
    form_class = EmailOrUsernameAuthenticationForm
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["google_oauth_configured"] = _google_oauth_configured(self.request)
        return context


class OAuthEmailAutoLoginView(View):
    def get(self, request):
        email = (request.GET.get("email") or "").strip().lower()
        timestamp = (request.GET.get("ts") or "").strip()
        signature = (request.GET.get("sig") or "").strip()
        target_url = _safe_next_url(request, request.GET.get("next"))

        if not email or not timestamp or not signature:
            messages.error(request, "Lien OAuth incomplet (email/ts/sig).")
            return redirect("ui:login")

        ok, error = _oauth_signature_is_valid(email, timestamp, signature)
        if not ok:
            messages.error(request, error)
            return redirect("ui:login")

        user_model = get_user_model()
        users = list(
            user_model._default_manager.filter(email__iexact=email, is_active=True)[:2]
        )
        if len(users) == 1:
            login(request, users[0], backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, "Connexion OAuth reussie.")
            return redirect(target_url)

        if not users:
            messages.error(request, "Aucun compte local actif pour cet email.")
        else:
            messages.error(
                request,
                "Plusieurs comptes utilisent cet email. Utilisez le nom d'utilisateur + mot de passe.",
            )
        return redirect("ui:login")


def _github_headers():
    token = getattr(settings, "GITHUB_TOKEN", "")
    if not token:
        return None
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "pfe-platform",
    }


def _normalize_github_repository(value: str) -> str:
    repo = (value or "").strip()
    if not repo:
        return ""

    for prefix in ("https://github.com/", "http://github.com/", "git@github.com:"):
        if repo.startswith(prefix):
            repo = repo[len(prefix):]
            break

    if repo.endswith(".git"):
        repo = repo[:-4]

    return repo.strip("/")


def _github_api_request(method, url, payload=None, headers=None):
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, method=method)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8")
        except Exception:
            detail = ""
        raise HTTPError(exc.url, exc.code, f"{exc.reason} {detail}".strip(), exc.headers, None)


def _ensure_branch(owner, repo, base_branch, branch, headers):
    base_ref_url = f"https://api.github.com/repos/{owner}/{repo}/git/ref/heads/{base_branch}"
    base_ref = _github_api_request("GET", base_ref_url, headers=headers)
    base_sha = base_ref["object"]["sha"]

    branch_ref_url = f"https://api.github.com/repos/{owner}/{repo}/git/ref/heads/{branch}"
    try:
        _github_api_request("GET", branch_ref_url, headers=headers)
        return
    except HTTPError as exc:
        if exc.code != 404:
            raise

    create_ref_url = f"https://api.github.com/repos/{owner}/{repo}/git/refs"
    _github_api_request(
        "POST",
        create_ref_url,
        payload={"ref": f"refs/heads/{branch}", "sha": base_sha},
        headers=headers,
    )


def _upsert_file(owner, repo, path, content, branch, message, headers):
    encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    get_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
    sha = None
    try:
        existing = _github_api_request("GET", get_url, headers=headers)
        sha = existing.get("sha")
    except HTTPError as exc:
        if exc.code != 404:
            raise

    put_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    payload = {
        "message": message,
        "content": encoded,
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha
    result = _github_api_request("PUT", put_url, payload=payload, headers=headers)
    commit_sha = result.get("commit", {}).get("sha", "")
    return commit_sha


def _push_solution_to_github(examen, user, soumission_id, code_source):
    headers = _github_headers()
    if not headers:
        return False, "Configuration GitHub manquante (GITHUB_TOKEN).", ""

    repo = getattr(settings, "GITHUB_REPO", "")
    if not repo or "/" not in repo:
        return False, "Configuration GitHub manquante (GITHUB_REPO).", ""

    owner, repo_name = repo.split("/", 1)
    base_branch = getattr(settings, "GITHUB_BASE_BRANCH", "main")
    solutions_path = getattr(settings, "GITHUB_SOLUTIONS_PATH", "solutions")
    username = user.username.replace(" ", "_")
    branch = f"student-{username}"
    if not examen.url_tests_git or not examen.hash_tests:
        return False, "Examen sans configuration de tests (URL/Hash).", ""
    tests_repo = _normalize_github_repository(examen.url_tests_git)
    if "/" not in tests_repo:
        return False, "Configuration tests invalide (repo GitHub attendu).", ""

    base_dir = f"{solutions_path}/exam_{examen.id}/{username}"
    code_path = f"{base_dir}/Main.java"
    meta_path = f"{base_dir}/metadata.json"
    message = f"Soumission examen {examen.id} - {username}"

    try:
        _ensure_branch(owner, repo_name, base_branch, branch, headers)
        commit_sha = _upsert_file(owner, repo_name, code_path, code_source, branch, message, headers)
        metadata = json.dumps(
            {
                "soumission_id": soumission_id,
                "exam_id": examen.id,
                "student": username,
                "tests_repo": tests_repo,
                "tests_ref": examen.hash_tests,
                "language": "java",
                "entry_file": "Main.java",
            },
            ensure_ascii=False,
            indent=2,
        )
        _upsert_file(owner, repo_name, meta_path, metadata, branch, message, headers)
    except (HTTPError, URLError, KeyError, ValueError) as exc:
        return False, f"Erreur GitHub: {exc}", ""

    repo_url = f"https://github.com/{owner}/{repo_name}"
    return True, repo_url, commit_sha


@login_required
def home(request):
    profil = getattr(request.user, "profil", None)
    if profil is None:
        profil, created = Profil.objects.get_or_create(
            utilisateur=request.user,
            defaults={"role": "ETUDIANT"},
        )
        if created:
            messages.info(
                request,
                "Profil etudiant cree automatiquement pour ce compte.",
            )
    role = profil.role
    if role == "ETUDIANT":
        return redirect("ui:etudiant_dashboard")
    if role in ("ENSEIGNANT", "ADMIN"):
        return redirect("ui:enseignant_examens")
    messages.warning(request, "Profil/role manquant.")
    return redirect("admin:index")


@login_required
def logout_view(request):
    if request.method in ("GET", "POST"):
        logout(request)
        messages.info(request, "Vous etes deconnecte.")
        return redirect("ui:login")
    return redirect("ui:home")


@role_required("ETUDIANT")
def etudiant_dashboard(request):
    now = timezone.now()
    examens_base = Examen.objects.filter(groupes_autorises__membres=request.user).distinct()
    _synchroniser_statuts_examens(queryset=examens_base)

    examens_autorises = (
        examens_base.filter(
            statut__in=["PUBLIE", "EN_COURS"],
        )
    )

    examens_en_cours = examens_autorises.filter(
        heure_debut__lte=now,
        heure_fin__gte=now,
    ).order_by("heure_fin")
    examens_a_venir = examens_autorises.filter(heure_debut__gt=now).order_by("heure_debut")[:5]

    context = {
        "examens_en_cours": examens_en_cours,
        "examens_a_venir": examens_a_venir,
        "nb_en_cours": examens_en_cours.count(),
        "nb_a_venir": examens_autorises.filter(heure_debut__gt=now).count(),
        "nb_soumissions": Soumission.objects.filter(etudiant=request.user).count(),
        "nb_resultats": Resultat.objects.filter(soumission__etudiant=request.user).count(),
    }
    return render(request, "ui/student/dashboard.html", context)


@role_required("ETUDIANT")
def etudiant_examens(request):
    now = timezone.now()
    examens_base = Examen.objects.filter(groupes_autorises__membres=request.user).distinct()
    _synchroniser_statuts_examens(queryset=examens_base)
    examens = (
        examens_base.filter(
            statut__in=["PUBLIE", "EN_COURS"],
            heure_debut__lte=now,
            heure_fin__gte=now,
        )
        .exclude(soumissions__etudiant=request.user)
        .order_by("-heure_debut")
    )
    q = clean_search_term(request.GET.get("q"))
    if q:
        examens = examens.filter(titre__icontains=q)
    return render(request, "ui/student/examens_list.html", {"examens": examens, "q": q})


@role_required("ETUDIANT")
def etudiant_examen_detail(request, examen_id: int):
    now = timezone.now()
    examens_base = Examen.objects.filter(groupes_autorises__membres=request.user).distinct()
    _synchroniser_statuts_examens(queryset=examens_base)
    examen = get_object_or_404(
        examens_base.filter(
            statut__in=["PUBLIE", "EN_COURS"],
            heure_debut__lte=now,
            heure_fin__gte=now,
        ),
        pk=examen_id,
    )

    ma_soumission = (
        Soumission.objects.filter(examen=examen, etudiant=request.user)
        .select_related("resultat")
        .first()
    )
    if ma_soumission:
        messages.info(request, "Vous avez deja soumis pour cet examen.")
        return redirect("ui:etudiant_resultats")

    if request.method == "POST":
        code_source = (request.POST.get("code_source") or "").strip()
        if not code_source:
            messages.error(request, "Le code source est obligatoire.")
            return redirect("ui:etudiant_examen_detail", examen_id=examen.id)

        payload = {
            "examen": examen.id,
            "code_source": code_source,
        }
        serializer = SoumissionSerializer(data=payload, context={"request": request})
        if serializer.is_valid():
            soumission = serializer.save(etudiant=request.user, statut="EN_TEST")

            ok, repo_url, commit_sha = _push_solution_to_github(
                examen, request.user, soumission.id, code_source
            )
            if not ok:
                soumission.delete()
                messages.error(request, repo_url)
                return redirect("ui:etudiant_examen_detail", examen_id=examen.id)

            soumission.url_depot_git = repo_url
            soumission.hash_commit = commit_sha
            soumission.save(update_fields=["url_depot_git", "hash_commit"])
            messages.success(request, "Soumission envoyee. Tests en cours via CI/CD.")
            return redirect("ui:etudiant_resultats")

        for errors in serializer.errors.values():
            for err in errors:
                messages.error(request, str(err))

    return render(
        request,
        "ui/student/examen_detail.html",
        {"examen": examen, "ma_soumission": ma_soumission},
    )


@role_required("ETUDIANT")
def etudiant_soumissions(request):
    soumissions = (
        Soumission.objects.filter(etudiant=request.user)
        .select_related("examen")
        .order_by("-soumis_le")
    )
    q = clean_search_term(request.GET.get("q"))
    if q:
        soumissions = soumissions.filter(examen__titre__icontains=q)
    return render(
        request,
        "ui/student/soumissions_list.html",
        {"soumissions": soumissions, "q": q},
    )


@role_required("ETUDIANT")
def etudiant_resultats(request):
    resultats = (
        Resultat.objects.filter(soumission__etudiant=request.user)
        .select_related("soumission__examen")
        .order_by("-corrige_le")
    )
    return render(request, "ui/student/resultats_list.html", {"resultats": resultats})


@role_required("ENSEIGNANT", "ADMIN")
def enseignant_examens(request):
    examens = _enseignant_examens_queryset(request.user).order_by("-heure_debut")
    q = clean_search_term(request.GET.get("q"))
    if q:
        examens = examens.filter(titre__icontains=q)
    return render(request, "ui/teacher/examens_list.html", {"examens": examens, "q": q})


@role_required("ENSEIGNANT", "ADMIN")
def enseignant_examen_nouveau(request):
    if request.method == "POST":
        form = ExamenForm(request.POST, request.FILES)
        if form.is_valid():
            examen = form.save(commit=False)
            examen.cree_par = request.user
            examen.save()
            form.save_m2m()
            messages.success(request, "Examen cree.")
            return redirect("ui:enseignant_examen_detail", examen_id=examen.id)
    else:
        form = ExamenForm(initial={"statut": "BROUILLON"})

    return render(
        request,
        "ui/teacher/examen_form.html",
        {"form": form, "mode": "create", "examen": None, "soumissions": None, "resultats": None},
    )


@role_required("ENSEIGNANT", "ADMIN")
def enseignant_examen_detail(request, examen_id: int):
    examen = get_object_or_404(_enseignant_examens_queryset(request.user), pk=examen_id)

    if request.method == "POST":
        form = ExamenForm(request.POST, request.FILES, instance=examen)
        if form.is_valid():
            form.save()
            messages.success(request, "Examen mis a jour.")
            return redirect("ui:enseignant_examen_detail", examen_id=examen.id)
    else:
        form = ExamenForm(instance=examen)

    soumissions = (
        Soumission.objects.filter(examen=examen)
        .select_related("etudiant")
        .order_by("-soumis_le")[:20]
    )
    resultats = (
        Resultat.objects.filter(soumission__examen=examen)
        .select_related("soumission")
        .order_by("-corrige_le")[:20]
    )

    return render(
        request,
        "ui/teacher/examen_form.html",
        {
            "form": form,
            "mode": "edit",
            "examen": examen,
            "soumissions": soumissions,
            "resultats": resultats,
        },
    )


@role_required("ENSEIGNANT", "ADMIN")
def enseignant_soumissions(request):
    soumissions = (
        Soumission.objects.filter(examen__in=_enseignant_examens_queryset(request.user))
        .select_related("examen", "etudiant")
        .order_by("-soumis_le")
    )
    examen_id = clean_digit_filter(request.GET.get("examen"))
    if examen_id:
        soumissions = soumissions.filter(examen_id=int(examen_id))
    return render(
        request,
        "ui/teacher/soumissions_list.html",
        {"soumissions": soumissions, "examen_id": examen_id},
    )


@role_required("ENSEIGNANT", "ADMIN")
def enseignant_resultats(request):
    resultats = (
        Resultat.objects.filter(soumission__examen__in=_enseignant_examens_queryset(request.user))
        .select_related("soumission__examen")
        .order_by("-corrige_le")
    )
    examen_id = clean_digit_filter(request.GET.get("examen"))
    if examen_id:
        resultats = resultats.filter(soumission__examen_id=int(examen_id))
    return render(
        request,
        "ui/teacher/resultats_list.html",
        {"resultats": resultats, "examen_id": examen_id},
    )
