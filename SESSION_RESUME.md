# SESSION RESUME — GridCheck (Stand: nach L3-Commit 749062f6)

## Erster Befehl morgen früh (an die KI):
Lies zuerst .cursorrules, .cursor/rules/06-arbeitsweise-gridcheck.mdc, PROJECT_RULES.md, docs/WORKFLOW.md und DECISIONS.md.
Arbeite strikt danach. Eine Aufgabe pro Antwort. PowerShell-Einzeiler/Here-Strings.
Backup mit Timestamp vor jeder Dateiänderung. Keine Nebenkriegsschauplätze. Kein Raten.
Stack: FastAPI + PostgreSQL 16 + PostGIS + Alembic. Kein Supabase, kein Drizzle.

## Wo wir stehen
- ✅ L3 abgeschlossen: engine_revision_hash ist Pflichtparameter im Renderer
- ✅ Commit: 749062f6 "feat(reports): L3 engine_revision_hash als Pflichtparameter"
- ✅ 16/16 Renderer-Tests grün
- ⚠️ 3 failed + 12 errors bei test_projektierer_report etc. — Ursache: SQLAlchemy User.billing_entitlements hat multiple FK-Pfade ohne foreign_keys=Angabe
- ⚠️ Großer ungetrackter Stand: ~30 neue Files (billing.py, site_markers.py, ops_followups.py, mehrere Alembic-Migrationen, _milestone_backups/, viele *.txt Audit-Dumps)

## Nächste Aufgabe: L3.1 — Billing-FK-Fix
Vor jedem Code-Patch zuerst diagnostizieren (kein Raten!):

1. pytest auf test_billing_package_access.py laufen lassen
2. alembic upgrade head prüfen
3. Liste aller Migrationen in backend/alembic/versions/ checken
4. Erst dann: foreign_keys= an User.billing_entitlements ergänzen

## Danach (priorisierte Backlog)
- L3.2: Ungetrackte Audit-/Dump-Dateien (*.txt) in .gitignore aufnehmen
- L3.3: Neue API-Module (billing, site_markers, ops_followups) reviewen & committen
- L4: engine_revision_hash auch in DB-Schema (reports-Tabelle) als NOT NULL erzwingen + Alembic-Migration

## Wichtige Regeln (aus .cursorrules)
- Revisionssicherheit: append-only, Hash-Chain
- Keine freie Netzkapazität ohne Beleg behaupten
- Keine Geschäftslogik im Frontend
- Datenquellen, Annahmen, Confidence getrennt halten
- Bei Regelverletzung: STOPP + sicherer Vorschlag
