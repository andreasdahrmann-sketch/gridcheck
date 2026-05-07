# GridCheck – Pre-Netzanschluss-Check App

**Faster Grid Connection Decisions – Powered by AI**

## Was ist GridCheck?
GridCheck ist ein diagnostisches Tool für Netzbetreiber und Projektierer zur schnellen Bewertung von Netzanschlussanfragen. Keine Ampellogik – sondern echte N-1-Analyse, Lastflussberechnung und KI-gestützte Empfehlungen.

## Tech Stack
- **Backend:** FastAPI (Python 3.11+), SQLAlchemy, pandapower
- **Frontend:** Next.js 15 App Router, React 19, TypeScript, shadcn/ui, Tailwind CSS 4
- **DB:** PostgreSQL 16
- **Auth:** JWT + OAuth2, rollenbasiert (admin, netzbetreiber, projektierer)
- **Package Manager:** pnpm (Frontend), pip (Backend)

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
Hinweis: Migrations bauen aufeinander auf (`20260507_01` Basisschema, `20260507_02` Query-Indizes).

Setze Umgebungsvariablen (PowerShell Beispiel):
```powershell
$env:APP_ENV="dev"
$env:DATABASE_URL="postgresql+psycopg://gridcheck:gridcheck_dev_2026@localhost:5432/gridcheck"
$env:CORS_ORIGINS="http://localhost:3000,http://localhost:5173"
$env:JWT_SECRET="replace-with-random-32-plus-char-secret"
$env:JWT_REFRESH_SECRET="replace-with-second-random-32-plus-char-secret"
$env:AUTO_CREATE_SCHEMA="false"
uvicorn main:app --reload
```

### 3) Frontend starten (API-Consumer)
```bash
cd frontend
npm install
npm run dev
```

Das Frontend ruft die API über den Proxy-Pfad `/api/backend/*` auf.

## ENV-Profile
- `backend/.env.example` -> lokales Development
- `backend/.env.staging.example` -> staging Baseline
- `backend/.env.prod.example` -> production Baseline

## Wichtige Regeln
- Revisionssicher: Jede Berechnung ist immutable gespeichert
- Prüf-IDs: CHK-YYYY-NNNNN
- Timestamps: immer UTC
- Soft-Delete überall (kein hartes DELETE)
- N-1-Kriterium wird bei jeder Berechnung geprüft
- TAB 2019 + VDE-AR-N 4100/4110/4120 als Regelwerk

## Deployment
Siehe docs/railway-deployment.md
