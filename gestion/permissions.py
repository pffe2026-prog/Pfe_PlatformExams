from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsEnseignantOrAdmin(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        profil = getattr(request.user, "profil", None)
        return bool(profil and profil.role in ("ENSEIGNANT", "ADMIN"))


class IsResultatEditor(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        profil = getattr(request.user, "profil", None)
        return bool(profil and profil.role in ("ENSEIGNANT", "ADMIN"))
