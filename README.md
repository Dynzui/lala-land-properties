# Lala Land Properties

Django + Wagtail + PostgreSQL modular monolith for the Lala Land Properties website and operations CMS.

## Supported stack

- Python 3.13
- Django 6.0.8
- Wagtail 7.4.3 LTS
- PostgreSQL for staging and production
- SQLite as a local-only fallback

## Local setup

From the repository root on Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Use `requirements.lock` for byte-for-byte reproducible environment rebuilds. `requirements.txt` lists the intentionally selected direct dependencies.

This workspace uses a project-local PostgreSQL 17 runtime on port `55432`. Start it with:

```powershell
.\scripts\start-local-postgres.ps1
```

Start or restart a single Django development server with:

```powershell
.\scripts\run-dev-server.ps1 -Port 8000 -PostgresPort 55432
```

The restart script removes stale Python development servers already bound to that exact port,
which prevents the browser from alternating between old and new templates.

Local database settings live in the Git-ignored `lala_land/settings/local.py`. The application
uses the restricted `lala_land` role; automated tests use the separate `lala_land_test` role.
SQLite remains available as an explicit lightweight fallback in environments without the local
settings file.

## Quality checks

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
```

## Project modules

- `accounts`: identities, roles, authentication, MFA, and sessions
- `properties`: locations, developments, variants, properties, and property types
- `listings`: listings, offers, lifecycle, features, and search rules
- `inquiries`: visitor inquiries, assignments, statuses, and notes
- `access_requests`: temporary access to sensitive business/customer fields
- `audittrail`: append-only audit events and revision coordination
- `sitecontent`: Wagtail pages, Resources articles, navigation, and legal placeholders
- `media_library`: upload policy and media-processing integration
- `integrations`: replaceable email, storage, maps, analytics, spam, and monitoring adapters
- `dashboard`: Owner/Admin operational views

## Production rules

Production requires PostgreSQL, a persistent media volume, a secret key, an allowed public host,
and an SMTP host for inquiry alerts. Set the sender and SMTP values shown in `.env.example`, then
set the private alert recipient under **Website content → Contact page settings** in the CMS.
Migrations are a separate release step; the application container must not silently migrate the
production database at startup.

The initial Render deployment is defined in `render.yaml`. See
[`docs/DEPLOY_RENDER.md`](docs/DEPLOY_RENDER.md) for the exact setup, cost, and launch checks.
