from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm

from gestion.input_security import clean_plain_text
from gestion.models import Examen


class EmailOrUsernameAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Email ou nom d'utilisateur",
        max_length=254,
        widget=forms.TextInput(attrs={"autofocus": True, "class": "form-control"}),
    )
    password = forms.CharField(
        label="Mot de passe",
        strip=False,
        widget=forms.PasswordInput(
            attrs={"autocomplete": "current-password", "class": "form-control"}
        ),
    )

    error_messages = {
        **AuthenticationForm.error_messages,
        "multiple_email_accounts": "Plusieurs comptes sont lies a cet email.",
    }

    def clean(self):
        identifier = (self.cleaned_data.get("username") or "").strip()
        if identifier and "@" in identifier:
            user_model = get_user_model()
            matches = list(
                user_model._default_manager.filter(email__iexact=identifier).only("username")[:2]
            )
            if len(matches) == 1:
                self.cleaned_data["username"] = matches[0].get_username()
            elif len(matches) > 1:
                raise forms.ValidationError(
                    self.error_messages["multiple_email_accounts"],
                    code="multiple_email_accounts",
                )

        return super().clean()


class ExamenForm(forms.ModelForm):
    class Meta:
        model = Examen
        fields = [
            "titre",
            "description",
            "heure_debut",
            "heure_fin",
            "statut",
            "groupes_autorises",
            "url_tests_git",
            "hash_tests",
            "pdf_examen",
        ]
        widgets = {
            "titre": forms.TextInput(attrs={"maxlength": 200}),
            "description": forms.Textarea(attrs={"rows": 4}),
            "heure_debut": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "heure_fin": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "groupes_autorises": forms.CheckboxSelectMultiple(),
            "pdf_examen": forms.ClearableFileInput(),
            "hash_tests": forms.TextInput(attrs={"maxlength": 40}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["heure_debut"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["heure_fin"].input_formats = ["%Y-%m-%dT%H:%M"]
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxSelectMultiple):
                continue
            if isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
                continue
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (css + " form-control").strip()

    def clean_titre(self):
        return clean_plain_text(self.cleaned_data.get("titre"), "Le titre")

    def clean_description(self):
        return clean_plain_text(self.cleaned_data.get("description"), "La description")

    def clean(self):
        cleaned_data = super().clean()
        debut = cleaned_data.get("heure_debut")
        fin = cleaned_data.get("heure_fin")
        statut = cleaned_data.get("statut", getattr(self.instance, "statut", "BROUILLON"))
        pdf_examen = cleaned_data.get("pdf_examen") or getattr(self.instance, "pdf_examen", None)
        if debut and fin and fin <= debut:
            self.add_error("heure_fin", "La date de fin doit etre apres la date de debut.")

        if statut != "BROUILLON" and not pdf_examen:
            self.add_error("pdf_examen", "Le PDF de l examen est obligatoire hors brouillon.")

        if self.instance and self.instance.pk and self.instance.statut != "BROUILLON":
            url_tests_git = cleaned_data.get("url_tests_git")
            hash_tests = cleaned_data.get("hash_tests")
            if (
                url_tests_git != self.instance.url_tests_git
                or hash_tests != self.instance.hash_tests
            ):
                self.add_error(
                    "url_tests_git",
                    "Les tests ne peuvent plus etre modifies apres publication.",
                )
        return cleaned_data
