# Szenarienvergleich — Stand & Lücken

**Stand:** 2026-05-19

## Was existiert

| Bereich | Status |
|---------|--------|
| Thermische Szenarien **innerhalb** einer Analyse | Tabelle in `GridCheckForm` / Engine-Output `szenarien[]` |
| Projekt speichert **letzte** Analyse | `projects.role_results` (ein Snapshot) |
| Analyse-History (Metadaten) | `GET /api/v1/analysis/history` — Score, `revision_hash`, kein volles Ergebnis |
| **MVP UI** | `/projects/[id]/szenarien-vergleich` — bis zu 2 lokale Snapshots + Side-by-Side |

## Was fehlt (eigenes Projekt)

1. **Serverseitige Run-History pro Projekt** — `GET /api/v1/projects/{id}/analysis-runs` mit gespeichertem Ergebnis-JSON (oder Revision-Pointer).
2. **Revision laden (User)** — heute `GET /api/v1/revisions/{hash}` nur **Admin**; für Vergleich braucht es scoped User-Zugriff + BOLA-Tests.
3. **Was-wäre-wenn** (ADR-003) — Eingabevarianten speichern, nicht nur thermische Engine-Szenarien.
4. **Diff-Engine** — strukturierter Vergleich von Scores, N-1-Level, Kostenbandbreite mit Audit-ID beider Runs.

## MVP-Verhalten (lokal)

Nach jeder erfolgreichen Projektanalyse werden bis zu **zwei** kompakte Snapshots in `sessionStorage` gehalten (`gridcheck:compare:{projectId}`). Die Vergleichsseite zeigt Kennzahlen Side-by-Side — **ohne** Kapazitäts- oder Zusage-Claims.

## Akzeptanz später (Vollfeature)

- Nutzer wählt zwei beliebige abgeschlossene Runs desselben Projekts.
- Anzeige: Score, Fazit, Worst-Case-Szenario, N-1-Level, Kostenbandbreite, `revision.hash`.
- Export-PDF „Szenarienvergleich“ mit Disclaimer.
