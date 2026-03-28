from datetime import timedelta
import os
from pathlib import Path
import sys

import django


BASE_DIR = Path(__file__).resolve().parents[1]
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "plateforme.settings")
os.chdir(BASE_DIR)
sys.path.insert(0, str(BASE_DIR))

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.utils import timezone  # noqa: E402

from gestion.models import Examen, GroupeAcademique, Profil, Resultat, Soumission  # noqa: E402


DEMO_GROUP_NAME = "PLAYWRIGHT-GI"
DEMO_ACADEMIC_YEAR = "2025-2026"
ACTIVE_EXAM_TITLE = "Playwright Student Active Exam"
UPCOMING_EXAM_TITLE = "Playwright Student Upcoming Exam"
RESULT_EXAM_TITLE = "Playwright Student Corrected Exam"


def ensure_user(*, username, email, password, role):
    user_model = get_user_model()
    user, _ = user_model.objects.get_or_create(
        username=username,
        defaults={
            "email": email,
            "is_active": True,
        },
    )
    user.email = email
    user.is_active = True
    user.set_password(password)
    user.save()

    Profil.objects.update_or_create(
        utilisateur=user,
        defaults={"role": role},
    )
    return user


def ensure_exam(*, teacher, title, description, start_at, end_at, status):
    exam, _ = Examen.objects.get_or_create(
        titre=title,
        cree_par=teacher,
        defaults={
            "description": description,
            "heure_debut": start_at,
            "heure_fin": end_at,
            "statut": status,
        },
    )
    exam.description = description
    exam.heure_debut = start_at
    exam.heure_fin = end_at
    exam.statut = status
    exam.url_tests_git = None
    exam.hash_tests = ""
    exam.save()
    return exam


def main():
    username = os.environ.get("PLAYWRIGHT_DEMO_TEACHER_USERNAME", "demo_teacher")
    email = os.environ.get("PLAYWRIGHT_DEMO_TEACHER_EMAIL", "demo.teacher@example.com")
    password = os.environ.get("PLAYWRIGHT_DEMO_TEACHER_PASSWORD", "DemoPass123!")
    student_username = os.environ.get("PLAYWRIGHT_DEMO_STUDENT_USERNAME", "demo_student")
    student_email = os.environ.get("PLAYWRIGHT_DEMO_STUDENT_EMAIL", "demo.student@example.com")
    student_password = os.environ.get("PLAYWRIGHT_DEMO_STUDENT_PASSWORD", "DemoPass123!")

    teacher = ensure_user(
        username=username,
        email=email,
        password=password,
        role="ENSEIGNANT",
    )
    student = ensure_user(
        username=student_username,
        email=student_email,
        password=student_password,
        role="ETUDIANT",
    )

    group, _ = GroupeAcademique.objects.get_or_create(
        nom=DEMO_GROUP_NAME,
        annee_academique=DEMO_ACADEMIC_YEAR,
    )
    group.membres.add(student)

    now = timezone.now()
    active_exam = ensure_exam(
        teacher=teacher,
        title=ACTIVE_EXAM_TITLE,
        description="Examen en cours pour la demonstration Playwright etudiant.",
        start_at=now - timedelta(minutes=15),
        end_at=now + timedelta(minutes=45),
        status="PUBLIE",
    )
    active_exam.groupes_autorises.set([group])

    upcoming_exam = ensure_exam(
        teacher=teacher,
        title=UPCOMING_EXAM_TITLE,
        description="Examen a venir visible depuis le tableau de bord etudiant.",
        start_at=now + timedelta(days=1),
        end_at=now + timedelta(days=1, hours=1),
        status="PUBLIE",
    )
    upcoming_exam.groupes_autorises.set([group])

    result_exam = ensure_exam(
        teacher=teacher,
        title=RESULT_EXAM_TITLE,
        description="Examen deja corrige pour presenter la page resultats.",
        start_at=now - timedelta(days=2, hours=1),
        end_at=now - timedelta(days=2),
        status="PUBLIE",
    )
    result_exam.groupes_autorises.set([group])

    submission, _ = Soumission.objects.get_or_create(
        examen=result_exam,
        etudiant=student,
        defaults={
            "url_depot_git": "https://github.com/example/demo-student-solution",
            "hash_commit": "playwright-demo-commit",
            "code_source": "public class Main { public static void main(String[] args) {} }",
            "statut": "CORRIGE",
        },
    )
    submission.url_depot_git = "https://github.com/example/demo-student-solution"
    submission.hash_commit = "playwright-demo-commit"
    submission.code_source = "public class Main { public static void main(String[] args) {} }"
    submission.statut = "CORRIGE"
    submission.save()

    Resultat.objects.update_or_create(
        soumission=submission,
        defaults={
            "note": "16.50",
            "feedback": "Resultat de demonstration Playwright.",
        },
    )

    print(f"Seeded Playwright demo teacher: {username}")
    print(f"Seeded Playwright demo student: {student_username}")


if __name__ == "__main__":
    main()
