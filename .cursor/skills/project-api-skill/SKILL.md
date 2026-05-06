---
name: project-api-skill
description: Standardisiert API-Arbeit in diesem Gridcheck-Projekt. Use when implementing or reviewing backend API endpoints, request/response schemas, error contracts, API versioning, validation, security checks, or API tests.
---

# Project API Skill (Gridcheck)

## Ziel
Dieser Skill erzwingt eine konsistente, revisionssichere API-Umsetzung für dieses Projekt.

## Wann nutzen
Nutze diesen Skill immer, wenn es um API-Endpunkte, Contracts, Validierung, Fehlerobjekte, Versionierung oder API-Tests geht.

## Verbindliche Leitplanken
1. Endpunkte unter `/api/v1/...`.
2. Businesslogik nicht im Router, nur Delegation an Services.
3. Request/Response über Pydantic v2-Schemas, keine rohen Dict-Pipelines.
4. Fehlerobjekt konsistent: `{ code, message, hint }` in `detail`.
5. Rechenkerne deterministisch, nachvollziehbar, mit Annahmen + Normversion.
6. Keine Kapazitätszusagen ohne verifizierte Netzbetreiberdaten.
7. Sicherheitsgrundlagen immer prüfen: Input-Validation, AuthZ/AuthN, BOLA, Secret-Leaks.

## Standard-Workflow
1. Ziel und Scope klären (eine Aufgabe, minimal-invasiv).
2. Betroffene Dateien lesen (Router, Schema, Service, Tests).
3. Contract zuerst definieren/prüfen (Input, Output, Fehlerfälle).
4. Endpoint implementieren oder anpassen.
5. Tests ergänzen (Happy Path + mindestens 1 negativer Fall).
6. Lint/Tests ausführen und Ergebnis dokumentieren.

## Contract-Checklist
- Request-Schema typisiert, Feldnamen mit Einheiten wo sinnvoll (`p_kw`, `u_kv`).
- Response-Schema explizit (`response_model=...`).
- Fehlerfälle enthalten maschinenlesbaren `code` und nutzbaren `hint`.
- Norm-/Version-Hinweise werden nicht unterschlagen, wenn fachlich relevant.

## Sicherheits-Checklist
- Untrusted Input strikt validiert.
- Keine sensiblen Daten im Log.
- Rechte-/Mandantengrenzen geprüft (BOLA vermeiden).
- Rate-Limiting für teure/public Endpoints berücksichtigt.

## Test-Checklist
- Positiver Hauptfall.
- Mindestens ein Validierungsfehler (422/400 je nach Design).
- Mindestens ein fachlicher Fehlerfall mit korrekt strukturiertem `detail`.
- Regressionstest bei Bugfix.

## Ausgabeformat bei API-Arbeit
Kurzes Ergebnis mit:
1. Geänderte Dateien
2. Contract-Änderung
3. Sicherheitsauswirkungen
4. Tests (ausgeführt/offen)

## Referenz
Für detailiertere Prüfungen: [API_CHECKLIST.md](API_CHECKLIST.md)
