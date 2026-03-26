from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import redirect

from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


def _extract_email_from_sociallogin(sociallogin) -> str:
    for email_address in getattr(sociallogin, "email_addresses", []) or []:
        email = (getattr(email_address, "email", "") or "").strip().lower()
        if email:
            return email

    user = getattr(sociallogin, "user", None)
    email = (getattr(user, "email", "") or "").strip().lower()
    if email:
        return email

    account = getattr(sociallogin, "account", None)
    extra_data = getattr(account, "extra_data", None)
    if isinstance(extra_data, dict):
        email = (extra_data.get("email") or "").strip().lower()
        if email:
            return email

    return ""


def _safe_error_message(request, text: str) -> None:
    try:
        messages.error(request, text)
    except Exception:
        # Can happen in edge-cases if messages middleware/storage is absent.
        pass


class ExistingUserOnlySocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        if getattr(getattr(request, "user", None), "is_authenticated", False):
            return
        if getattr(sociallogin, "is_existing", False):
            return

        email = _extract_email_from_sociallogin(sociallogin)
        if not email:
            _safe_error_message(request, "Connexion Google refusee: email introuvable.")
            raise ImmediateHttpResponse(redirect("ui:login"))

        user_model = get_user_model()
        users = list(
            user_model._default_manager.filter(email__iexact=email, is_active=True).only("id")[
                :2
            ]
        )
        if len(users) == 1:
            return

        if not users:
            _safe_error_message(
                request,
                "Connexion Google refusee: cet email n'existe pas dans la plateforme.",
            )
        else:
            _safe_error_message(
                request,
                "Connexion Google refusee: plusieurs comptes locaux utilisent cet email.",
            )
        raise ImmediateHttpResponse(redirect("ui:login"))
