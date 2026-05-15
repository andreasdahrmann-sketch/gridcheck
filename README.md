# GridCheck – Pre-Netzanschluss-Check App

**Faster Grid Connection Decisions – Powered by AI**

## Was ist GridCheck?
GridCheck ist ein diagnostisches Tool für Netzbetreiber und Projektierer zur schnellen Bewertung von Netzanschlussanfragen. Keine Ampellogik – sondern echte N-1-Analyse, Lastflussberechnung und KI-gestützte Empfehlungen.

## Tech Stack
- **Backend:** FastAPI (Python 3.11+), SQLAlchemy, pandapower
- **Frontend:** Next.js 14 App Router, React 18, TypeScript, Radix UI, Tailwind CSS 3
- **DB:** PostgreSQL 16 + PostGIS
- **Auth:** JWT + OAuth2, rollenbasiert (admin, netzbetreiber, projektierer)
- **Package Manager:** npm (Frontend), pip (Backend)

## Projektstruktur
\\\
gridcheck/
├── backend/
│   ├── main.py
│   ├── constants.py
│   ├── requirements.txt
│   ├── api/
│   ├── audit/
│   ├── db/
│   ├── engine/        # berechnung.py, ki_modul.py, pdf_report.py, revision.py
│   └── services/      # netzcheck.py
├── frontend/
│   ├── app/           # Next.js App Router
│   ├── components/
│   │   ├── gridcheck/
│   │   ├── dashboard/ # NetzbetreiberDashboard.tsx
│   │   └── ui/        # shadcn/ui
│   └── lib/
└── docs/
    ├── ui-guidelines.md
    └── railway-deployment.md
\\\

## Lokale Entwicklung (Docker + API + Postgres)

### 1) Infrastruktur starten (Docker)
```bash
docker compose up -d postgres redis
```

### 2) Backend starten (Python venv)
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Schema-Migration (empfohlen statt auto create):
```bash
cd backend
alembic upgrade head
```
Hinweis:
- `alembic` verwendet die aktive `DATABASE_URL` aus Ihrer Shell bzw. `backend/.env`
- Migrations bauen aufeinander auf (`20260507_01` Basisschema, `20260507_02` Query-Indizes, `20260511_01` Monetization-History, `20260511_02` Package-/Entitlement-Layer).

Setze Umgebungsvariablen (PowerShell Beispiel):
```powershell
$env:APP_ENV="dev"
$env:DATABASE_URL="postgresql+psycopg2://gridcheck:gridcheck_dev_2026@localhost:5433/gridcheck"
$env:CORS_ORIGINS="http://localhost:3000,http://localhost:5173"
$env:JWT_SECRET="replace-with-random-32-plus-char-secret"
$env:JWT_REFRESH_SECRET="replace-with-second-random-32-plus-char-secret"
$env:AUTO_CREATE_SCHEMA="false"
uvicorn main:app --reload
```

Alternativ mit `backend/.env.example` starten:
```powershell
Copy-Item .\backend\.env.example .\backend\.env
```

### 3) Frontend starten (API-Consumer)
```bash
cd frontend
npm install
npm run dev
```

Das Frontend ruft die API ueber den Proxy-Pfad `/api/backend/*` auf. In Deployments auf Vercel bleibt dieser Pfad gleich; `frontend/next.config.mjs` rewritet serverseitig auf `BACKEND_URL`.

## Mobile Shell (Android/iOS)

Die bestehende Next.js-/PWA-App bleibt der Hauptpfad. Fuer Android und iOS ist jetzt eine minimale Capacitor-Shell als
saubere Build-Basis vorbereitet, ohne den Web-/PWA-Ansatz umzubauen.

Kurzablauf:

```powershell
cd .\frontend
# Fuer Capacitor 8 native Commands: Node 22+
npm install
$env:CAPACITOR_SERVER_URL="https://staging.example.gridcheck.de"
npm run native:add:android
npm run native:add:ios
npm run native:sync
```

Danach die Plattformen in den nativen IDEs oeffnen:

```powershell
npm run native:open:android
npm run native:open:ios
```

Details, ENV-Hinweise und Restpunkte fuer Signing/Store siehe `docs/mobile-capacitor.md`.

## Final Verification

Fuer den finalen Repo-Check gibt es einen einzigen offensichtlichen Root-Einstiegspunkt:

```powershell
.\Verify-Finalization.cmd
```

Der Skriptlauf fuehrt nacheinander aus:

- `python -m alembic upgrade head`
- `python -m pytest tests/test_auth_projects_api.py tests/test_stakeholder_reports_vnb_invest.py tests/test_billing_package_access.py`
- `npm run lint`
- `npm run build`

Voraussetzung: ein laufendes lokales PostgreSQL auf Docker-Port `5433`.
Standard-Test-URL fuer Verifikation und Tests:

```powershell
$env:TEST_DATABASE_URL="postgresql+psycopg2://gridcheck:gridcheck_dev_2026@localhost:5433/gridcheck_test"
```

Optionale Teillaeufe:

```powershell
.\Verify-Finalization.cmd -SkipFrontend
.\Verify-Finalization.cmd -SkipBackend
```

Direkter PowerShell-Aufruf ist ebenfalls moeglich:

```powershell
powershell -ExecutionPolicy Bypass -File .\Verify-Finalization.ps1
```

## Lokaler Schnellstart

### Backend
```powershell
.\Start-Local.cmd
```

### Frontend
```powershell
cd .\frontend
npm install
npm run dev
```

Oder manuell:

```powershell
docker compose up -d postgres redis
Copy-Item .\backend\.env.example .\backend\.env -ErrorAction SilentlyContinue
cd .\backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m alembic upgrade head
uvicorn main:app --reload
```

## ENV-Profile
- `backend/.env.example` -> lokales Development
- `backend/.env.staging.example` -> staging Baseline
- `backend/.env.prod.example` -> production Baseline
- `frontend/.env.example` -> lokale/Vercel-Frontend-Basis mit Rewrite auf das Backend

## Wichtige Regeln
- Revisionssicher: Jede Berechnung ist immutable gespeichert
- Prüf-IDs: CHK-YYYY-NNNNN
- Timestamps: immer UTC
- Soft-Delete überall (kein hartes DELETE)
- N-1-Kriterium wird bei jeder Berechnung geprüft
- TAB 2019 + VDE-AR-N 4100/4110/4120 als Regelwerk

## Deployment
Empfohlenes MVP-Zielbild:

- `frontend/` auf Vercel (Root Directory `frontend`)
- `backend/` separat deployt mit PostgreSQL und `/health`
- Frontend bleibt per `/api/backend/*` same-origin und rewritet intern auf `BACKEND_URL`

Die konkrete Schritt-fuer-Schritt-Anleitung steht in `docs/railway-deployment.md`.

## Deploy-Checkliste (CI-Schutz)
- GitHub Actions `CI` muss gruen sein.
- Backend-Job erfolgreich:
  - `alembic upgrade head`
  - `pytest -q tests/test_auth_projects_api.py tests/test_stakeholder_reports_vnb_invest.py tests/test_billing_package_access.py`
- Frontend-Job erfolgreich:
  - `npm run lint`
  - `npm run build`
- In staging/prod sind Pflicht-ENV gesetzt (mindestens `DATABASE_URL`, `JWT_SECRET`, `JWT_REFRESH_SECRET`, `CORS_ORIGINS` oder `CORS_ORIGIN_REGEX`, `TRUSTED_HOSTS`, `BACKEND_URL`, `PROJECT_UPLOAD_DIR`, `SITE_MARKER_UPLOAD_DIR`).
