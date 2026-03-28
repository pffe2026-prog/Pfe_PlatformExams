# Pfe Platform Exams

Application Django de gestion d'examens avec interface enseignant/etudiant, API REST, soumissions de code et retour de correction via webhook.

## Fonctionnalites
- Gestion des utilisateurs avec roles `ADMIN`, `ENSEIGNANT` et `ETUDIANT`
- Creation et gestion des examens
- Acces controle par groupes academiques
- Soumission de code et suivi des resultats
- API REST pour les ressources principales
- Workflow CI/CD avec webhook de correction
- Connexion locale et integration OAuth Google

## Stack
- Django 6
- Django REST Framework
- django-allauth
- MySQL en production, SQLite en developpement

## Installation
```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py createsuperuser
.\.venv\Scripts\python manage.py runserver
```

## Configuration
Le fichier `.env.example` contient les variables principales:
- `DEBUG`
- `SECRET_KEY`
- `API_WEBHOOK_TOKEN`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`
- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`

## Acces
- Interface web: `http://127.0.0.1:8000/`
- Administration: `http://127.0.0.1:8000/admin/`
- API REST: `http://127.0.0.1:8000/api/`

## Tests
```powershell
python manage.py test
```

## Tests E2E avec Playwright
```powershell
npm install
npx playwright install chromium
npm run test:e2e
```

Les tests Playwright demarrent Django automatiquement, appliquent les migrations locales, creent des comptes de demo et executent:
- un scenario enseignant: connexion + creation d examen en brouillon
- un scenario etudiant: connexion + consultation du tableau de bord, d un examen en cours et des resultats

Pour la soutenance, utilisez le scenario complet et ralenti:
```powershell
npm run test:e2e:demo
```

Ce scenario montre dans le meme enchainement:
- enseignant: creation d un examen publie
- etudiant: ouverture de l examen, soumission et consultation du resultat final

Comptes de demo utilises par Playwright:
- username: `demo_teacher`
- password: `DemoPass123!`
- username: `demo_student`
- password: `DemoPass123!`

## Donnees de demonstration
Le fichier `fixtures/demo.json` peut etre utilise pour charger un jeu de donnees de demo.
