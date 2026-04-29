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

## Lokale Entwicklung

### Backend
\\\ash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
\\\

### Frontend
\\\ash
cd frontend
pnpm install
pnpm dev
\\\

## Wichtige Regeln
- Revisionssicher: Jede Berechnung ist immutable gespeichert
- Prüf-IDs: CHK-YYYY-NNNNN
- Timestamps: immer UTC
- Soft-Delete überall (kein hartes DELETE)
- N-1-Kriterium wird bei jeder Berechnung geprüft
- TAB 2019 + VDE-AR-N 4100/4110/4120 als Regelwerk

## Deployment
Siehe docs/railway-deployment.md
