from django.urls import path

from . import views

app_name = "ui"

urlpatterns = [
    path("", views.home, name="home"),
    path("connexion/", views.EmailLoginView.as_view(), name="login"),
    path("connexion/oauth-email/", views.OAuthEmailAutoLoginView.as_view(), name="oauth_email_login"),
    path("deconnexion/", views.logout_view, name="logout"),
    path("etudiant/", views.etudiant_dashboard, name="etudiant_dashboard"),
    path("etudiant/examens/", views.etudiant_examens, name="etudiant_examens"),
    path("etudiant/examens/<int:examen_id>/", views.etudiant_examen_detail, name="etudiant_examen_detail"),
    path("etudiant/soumissions/", views.etudiant_soumissions, name="etudiant_soumissions"),
    path("etudiant/resultats/", views.etudiant_resultats, name="etudiant_resultats"),
    path("enseignant/examens/", views.enseignant_examens, name="enseignant_examens"),
    path("enseignant/examens/nouveau/", views.enseignant_examen_nouveau, name="enseignant_examen_nouveau"),
    path("enseignant/examens/<int:examen_id>/", views.enseignant_examen_detail, name="enseignant_examen_detail"),
    path("enseignant/soumissions/", views.enseignant_soumissions, name="enseignant_soumissions"),
    path("enseignant/resultats/", views.enseignant_resultats, name="enseignant_resultats"),
]
