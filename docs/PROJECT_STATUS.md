# GridCheck – Project Status
> Zuletzt aktualisiert: 2026-05-16

## Installierte Dependencies

### Frontend (`frontend/`)
- Next.js 14.2.x, React 18, TypeScript (strict)
- Tailwind CSS v4, shadcn/ui-Komponenten unter `components/ui/`
- TanStack Query, Leaflet, Recharts, Lucide

### Backend (`backend/`)
- Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.x
- PostgreSQL 16 + PostGIS (lokal Docker Port 5433)
- Alembic-Migrationen, pytest

## Erledigte Features (Auszug)
- [x] Monorepo-Struktur `frontend/` + `backend/`
- [x] Netzanschluss-Engine (`engine/berechnung.py`) inkl. N-1-Screening
- [x] Stakeholder-PDF-Reports (Projektierer, VNB, Invest)
- [x] JWT-Auth Backend + Frontend-Session (`bearerAuthHeaders`)
- [x] Projekt-CRUD (`/api/v1/projects`) + geschützte UI-Routen
- [x] PLZ→VNB-Lookup (`/api/v1/geo/plz/{plz}`) mit kuratiertem Datensatz
- [x] Frontend↔Backend über `/api/backend`-Rewrite (`BACKEND_URL`)
- [x] Disclaimer-Komponente (`AnalysisDisclaimer`) in Check- und Projekt-UI
- [x] KI-Feedback-API (`/api/v1/ki/*`) mit Hash-Chain
- [x] Revisionssichere Audit-Tabellen (PostgreSQL, Alembic)

## Offene TODOs (priorisiert)
- [ ] Produktions-Deploy stabil verifizieren (Vercel `BACKEND_URL`, Railway Health)
- [ ] GIS-/Netzdatenpipeline (OSM/DSO) als eigener Meilenstein
- [ ] Security-Onepager / AVV für Enterprise-Procurement
- [ ] Pilotangebot und Demo-Cases schriftlich freigeben
- [ ] E2E-Smoke (Playwright) optional ergänzen

## Bekannte Bugs / Hinweise
- **`page.tsx` (Startseite):** Kein duplizierter Code mehr (Stand 2026-05-16); früherer Eintrag obsolet.
- **Deployment:** Stabilität hängt von gesetzten Prod-ENV ab (nicht im Repo).

## Meilensteine
| Nr | Beschreibung | Datum |
|----|-------------|-------|
| M1 | Grundstruktur + Stakeholder-Routen | 2026-05-02 |
| M2 | PostgreSQL + Alembic | 2026-05-10 |
| M3 | Live-API-Integration Frontend | 2026-05-16 |
