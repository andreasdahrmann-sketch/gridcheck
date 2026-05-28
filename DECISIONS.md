# Architecture Decisions Log

| #   | Datum      | Entscheidung                                                        | Begruendung                                              |
|-----|------------|---------------------------------------------------------------------|----------------------------------------------------------|
| 001 | 2026-05-02 | Getrennte Routen pro Stakeholder (/projektierer, /vnb, ...)         | Saubere UX, klare Monetarisierung                        |
| 002 | 2026-05-02 | Phasenreihenfolge Projektierer -> VNB -> Invest                     | Hoechste Nutzerzahl zuerst, dann hoechster Lizenzwert    |
| 003 | 2026-05-02 | Killer Phase 1 = Was-waere-wenn-Optimierer schlank (Var. a)         | MVP-Fokus, kein Verzetteln                               |
| 004 | 2026-05-02 | Stack: FastAPI + React/TS + PostgreSQL 16 + PostGIS                 | SQLite war nur Startpunkt; PostgreSQL seit 2026-05 aktiv |
| 005 | 2026-05-02 | Revisionssicherheit via SHA256 Hash-Chain                           | Kostenfrei, ausreichend fuer MVP                         |
| 006 | 2026-05-02 | Gemeinsame Core-Engine, rollenspezifische Layer                     | Vermeidet Code-Duplikation                               |
| 007 | 2026-05-02 | AI liefert IMMER PowerShell-Befehle, nie rohe Markdown              | User arbeitet auf Windows PowerShell                     |
| 008 | 2026-05-10 | Datenbankwechsel SQLite -> PostgreSQL 16 + PostGIS (Port 5433)      | Geo-Funktionen, Skalierbarkeit, KRITIS-Anforderungen     |
| 009 | 2026-05-10 | Docker Desktop als verbindliche Laufzeitumgebung fuer alle Services | Reproduzierbarkeit, lokale Datenhoheit, kein Cloud-Vendor|
| 010 | 2026-05-10 | Schema-Management ausschliesslich via Alembic                       | Revisionssicher; Base.metadata.create_all() entfernt     |
| 011 | 2026-05-11 | PostgreSQL-only gilt auch fuer Tests, Skripte und Verifikation      | Keine aktive SQLite-Unterstuetzung mehr im Repo-Pfad     |
| 013 | 2026-05-24 | Kumulations-Check + NB-Georeferenz (Variante A für Projektierer, Variante C für verifizierte NBs) — **Vorgeschlagen** | Painpoint NB-Dashboard adressieren ohne Stack-Wechsel; PostGIS + bestehender Verifikations-Pfad genutzt |

---

## ADR-013: Kumulations-Check und NB-Georeferenz-Sicht

**Status:** Vorgeschlagen (Detailbegründung siehe `docs/decisions/ADR-013-kumulations-check-und-nb-georeferenz.md`)
**Datum:** 2026-05-24

### Beschluss (Kurzfassung)
- Neue Tabelle `grid_requests` (PostGIS, append-only Audit) als Cross-Project-Schicht.
- **Projektierer (eigene Daten):** Detailsicht.
- **Projektierer (fremde Daten):** nur aggregiert, k ≥ 3, PLZ-Centroid oder gerundeter Radius-Centroid.
- **Verifizierter NB (`vnb_verification_status='approved'`):** Detail im eigenen Gebiet, ohne Klarname Projektierer, mit View-Audit-Log.
- **Heatmap (Variante B):** **nicht** als Standard-Sicht für fremde Projektierer.
- Stack bleibt FastAPI + PostgreSQL + Alembic + Next.js 14 (kein Supabase, kein Stack-Wechsel — siehe ADR-007-DETAIL und `docs/PAINPOINT_NB_DASHBOARD.md` §7).

### Konsequenzen
- Migrations: neue Alembic-Migration `grid_requests` + Audit, rückwärts kompatibel (siehe BL-NB-001).
- Privacy: Aggregat-Endpoint hat k-Anonymität und Rate-Limit als Akzeptanzkriterien (BL-NB-003).
- VNB-Map ist neue gated Frontend-Route (BL-NB-004).
- „Digitale Vor-Einspeisezusage" (BL-NB-005) bleibt **nach** rechtlicher Klärung; GridCheck nur Trägermedium, VNB ist Aussteller.

### Status / nächste Schritte
- **Vor Code-Beginn:** Nutzer-Entscheidung zu offenen Fragen (`docs/PAINPOINT_NB_DASHBOARD.md` §8).
- **Erster Code-Schritt nach Freigabe:** BL-NB-001 (Schema + Alembic).

---

## ADR-008: Datenbankwechsel zu PostgreSQL 16 + PostGIS

**Status:** Final, aktiv seit 2026-05-10
**Abloest:** ADR-004 (SQLite-Teil)

### Beschluss
PostgreSQL 16 mit PostGIS-Extension ist die einzige persistente Datenbank.
SQLite wird nicht mehr verwendet, auch nicht fuer Tests (dort: PostgreSQL-Testinstance via Docker).

### Begruendung
- PostGIS ermoeglicht native Geo-Queries (Umkreissuche, Netzgebiete, Trassenfuehrung)
- Skalierbar auf Multi-User / VNB-Lizenzmodell
- KRITIS-konform (selbst-gehostet, EU, volle Datenhoheit)
- Append-only Audit-Tables + Hash-Chain nur robust mit ACID-DB

### Konsequenzen
- Port 5433 (lokal, Docker), Produktiv: EU-VPS oder dedizierter Server
- Connection via psycopg2 / SQLAlchemy
- Migrations: ausschliesslich Alembic (siehe ADR-010)
- Tests, CI und lokale Verifikationsskripte laufen ebenfalls gegen PostgreSQL

---

## ADR-009: Docker Desktop als verbindliche Laufzeitumgebung

**Status:** Final, aktiv seit 2026-05-10

### Beschluss
Alle persistenten Services (PostgreSQL, spaeter Redis, MinIO) laufen als Docker-Container.
Docker Desktop (Windows) ist Pflicht-Voraussetzung fuer die Entwicklungsumgebung.

### Begruendung
- Reproduzierbare Umgebungen (kein "works on my machine")
- Kein externes Cloud-Vendor-Lock-in
- Lokale Datenhoheit (DSGVO, KRITIS)
- Einfaches Backup via Docker Volumes

### Konsequenzen
- docker-compose.yml ist teil des Repositories
- Kein nativer Postgres-Install notwendig
- CI/CD spaeter: GitHub Actions mit Docker-in-Docker

---

## ADR-010: Schema-Management ausschliesslich via Alembic

**Status:** Final, aktiv seit 2026-05-10

### Beschluss
Base.metadata.create_all() wird aus main.py und allen anderen Stellen entfernt.
Alle Schemaenaderungen ausschliesslich als Alembic-Migration (versioniert, benannt).

### Begruendung
- Revisionssicherheit: jede Schemaanederung ist nachvollziehbar und datiert
- Kein Silent-Schema-Drift bei Server-Neustarts
- Pflicht fuer spaetere Audits (VNB-Lizenz, KRITIS)

### Konsequenzen
- Jede neue Tabelle / Spalte = neues alembic revision
- Migration-History ist Teil des Git-Repositories
- Rollback via alembic downgrade moeglich

---

## ADR-007-DETAIL: Kein Supabase

**Status:** Final, ueberstimmt Cursor-Rules
**Datum:** 2026-05-10

### Beschluss
FastAPI bleibt komplettes Backend. Supabase wird NICHT eingesetzt.

### Begruendung
- Supabase = Cloud-Service ohne volle Hoheit ueber Audit-Trails
- DSGVO-Risiko (US-Mutter, Datenresidenz unklar)
- Revisionssichere Audit-Logs muessen lokal/EU-souveraen sein
- GridCheck verarbeitet kritische Infrastrukturdaten (KRITIS)

### Konsequenzen
- Auth: FastAPI-eigen (JWT, bcrypt) - bereits vorhanden
- DB: PostgreSQL 16 + PostGIS (selbst-gehostet, EU) - bereits aktiv
- Realtime: SSE oder WebSocket via FastAPI
- File-Storage: lokales FS / S3-kompatibel (MinIO, EU)
- RBAC: eigene Implementierung in FastAPI
- Audit: Append-only Tables + Hash-Chain (revisionssicher)

### Cursor-Rules
Supabase-Verweise in .cursorrules wurden entfernt / als ungueltig markiert.

---

## 2026-05-13 — Schema-Drift-Auflösung vor Alembic-Upgrade auf 20260512_03

### Problem
Beim Versuch `alembic upgrade head` (von `b6b9e5a3cbd3` auf `20260512_03`) crashte Migration `20260510_01_data_source_models` mit `DuplicateTable`. Diagnose: 7 Tabellen aus `20260510_01` existierten bereits in der lokalen DB **ohne Alembic-Stempel** (vermutlich früher per `Base.metadata.create_all()` oder manuell angelegt).

### Betroffene Tabellen (alle leer, schema-identisch zur Migration)
`asset_candidates`, `generation_assets`, `system_signals`, `weather_resource`, `ground_risk`, `cost_indices`, `gridcheck_result_audit`

### Verifikation vor Eingriff
- `COUNT(*) = 0` für alle 7 Tabellen → kein Datenverlust-Risiko
- `\d <table>` verglichen mit Migration `20260510_01_data_source_models.py`: Spalten, Typen, NOT-NULL, PK, Indexe, FKs **identisch**
- Mini-Abweichung: `server_default` von String-Konstanten (`'0'`, `'UNKNOWN'`, `'C'`, `'{}'`) wird von `psql \d` nicht angezeigt — Anzeige-Artefakt, schema-irrelevant

### Auflösung (Variante: Drop + Re-Migrate, nicht `stamp`)
**Begründung gegen `alembic stamp head`**: Stampen hätte den Drift dauerhaft verschleiert. Drop + saubere Migration garantiert, dass DB-Zustand 1:1 dem Migrations-Code entspricht — Voraussetzung für Revisionssicherheit.

1. DB-Backup: `_milestone_backups/gridcheck_db_20260513_070016.sql` (pg_dump custom format)
2. `DROP TABLE ... CASCADE` für alle 7 verwaisten Tabellen
3. `python -m alembic upgrade head` → erfolgreich bis `20260512_03`
4. Verifikation: alle 14 erwarteten Tabellen vorhanden, `alembic current = 20260512_03 (head)`

### Lehre für künftig
- Kein `Base.metadata.create_all()` in Produktions-/Dev-DB außerhalb von Tests
- Bei jedem `upgrade`-Crash zuerst **vollständige Drift-Inventur** (alle Tabellen pro Migration), nicht nur Stichproben
- Schema-Vergleich vor `DROP` ist Pflicht, selbst wenn Tabellen leer sind

### Commits (Code-Stand, der zu dieser DB-Migration passt)
- `a2b70709` — feat(db): alembic migrations für data sources, monetization, package access, ops followup, site markers & revision chain
