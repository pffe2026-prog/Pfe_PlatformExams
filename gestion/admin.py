from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import (
    AdminUserCreationForm,
    UserChangeForm,
)

from .models import (
    Examen,
    GroupeAcademique,
    JournalAudit,
    Profil,
    Resultat,
    Soumission,
)


User = get_user_model()


class UserAdminCreationForm(AdminUserCreationForm):
    role = forms.ChoiceField(choices=Profil.ROLE_CHOICES, label="Role", required=True)

    class Meta(AdminUserCreationForm.Meta):
        model = User
        fields = ("username", "email", "first_name", "last_name")


class UserAdminChangeForm(UserChangeForm):
    role = forms.ChoiceField(choices=Profil.ROLE_CHOICES, label="Role", required=False)

    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get("instance")
        if not instance:
            return
        profil = getattr(instance, "profil", None)
        if profil:
            self.fields["role"].initial = profil.role


class UserAdmin(DjangoUserAdmin):
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Role Plateforme", {"fields": ("role",)}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("Role Plateforme", {"fields": ("role",)}),
    )

    @admin.display(description="Role")
    def role_display(self, obj):
        profil = getattr(obj, "profil", None)
        return profil.role if profil else "-"

    list_display = DjangoUserAdmin.list_display + ("role_display",)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        role = form.cleaned_data.get("role")
        if role:
            Profil.objects.update_or_create(
                utilisateur=obj,
                defaults={"role": role},
            )


try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
admin.site.register(User, UserAdmin)


@admin.register(Profil)
class ProfilAdmin(admin.ModelAdmin):
    list_display = ("utilisateur", "role")
    search_fields = ("utilisateur__username",)


@admin.register(GroupeAcademique)
class GroupeAcademiqueAdmin(admin.ModelAdmin):
    list_display = ("nom", "annee_academique")
    search_fields = ("nom", "annee_academique")
    filter_horizontal = ("membres",)


@admin.register(Examen)
class ExamenAdmin(admin.ModelAdmin):
    list_display = (
        "titre",
        "statut",
        "heure_debut",
        "heure_fin",
        "cree_par",
        "url_tests_git",
        "hash_tests",
    )
    list_filter = ("statut",)
    search_fields = ("titre", "cree_par__username")
    filter_horizontal = ("groupes_autorises",)
    fields = (
        "titre",
        "description",
        "heure_debut",
        "heure_fin",
        "statut",
        "cree_par",
        "url_tests_git",
        "hash_tests",
        "groupes_autorises",
    )


@admin.register(Soumission)
class SoumissionAdmin(admin.ModelAdmin):
    list_display = ("trace_id", "examen", "etudiant", "statut", "soumis_le")
    list_filter = ("statut",)
    search_fields = ("trace_id", "examen__titre", "etudiant__username")


@admin.register(Resultat)
class ResultatAdmin(admin.ModelAdmin):
    list_display = ("soumission", "note", "corrige_le")
    search_fields = ("soumission__trace_id",)


@admin.register(JournalAudit)
class JournalAuditAdmin(admin.ModelAdmin):
    list_display = ("utilisateur", "action", "horodatage")
    search_fields = ("utilisateur__username", "action")
