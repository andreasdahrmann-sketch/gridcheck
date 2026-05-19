# VNB-Kommunikation (Netzbetreiber-Austausch)

## Zweck

Geschützter Informationsaustausch **zwischen Verteilnetzbetreibern (VNB)** zu betrieblichen Themen (Kapazitätshinweise, Redispatch, Infrastruktur). Der Kanal ist **nicht öffentlich**, nicht für Projektierer/Investoren und ersetzt keine formelle Netzanschlussentscheidung.

## MVP-Scope

| Bereich | Im MVP | Später |
|--------|--------|--------|
| Threaded Nachrichten | Ja | — |
| Kategorien | Kapazitätshinweis, Redispatch, Infrastruktur, Sonstiges | Feinkategorien |
| Zielgruppe | Alle **verifizierten** NB-Nutzer (`netzbetreiber_verified`) | Org-Konten |
| Board | Gemeinsames Board **„Austausch“** (`board_scope=austausch`) | Regionale Boards, Teilnehmer-Threads |
| Anhänge | Nein | Datei-Upload mit Virenscan |
| Kapazitätszusage in Text | **Verboten** (Validator + UI-Hinweis) | — |
| Audit | Append-only pro Nachricht | Export für Compliance |

## Zugriff

- Rolle `netzbetreiber` **und** `users.vnb_verification_status = approved` (API-Feld `netzbetreiber_verified: true`).
- Admins haben **keinen** Standardzugriff (Support nur über separates Verfahren).
- API-Prefix: `/api/v1/vnb/comms/`
- Schreibzugriffe: JWT/Cookie-Auth, **CSRF** (Cookie-Clients), **Rate-Limit** wie andere Write-Endpoints.

## Datenmodell (vereinfacht)

```
vnb_threads
  - board_scope (MVP: "austausch")
  - title, category, target_vnb_region (optional)
  - created_by_user_id, timestamps

vnb_messages (append-only, keine Updates/Löschungen in API)
  - thread_id, sender_user_id, body, created_at

vnb_message_audit (append-only)
  - message_id, event_type, actor_user_id, payload_json, checksum
```

## Sicherheit & BOLA

- **MVP:** Jeder verifizierte NB sieht alle Threads im Board `austausch` (kein Cross-Org-Leak über Projekt-IDs).
- Keine Endkunden-PII in Nachrichten (E-Mail/Telefon-Muster werden abgewiesen).
- Keine Formulierungen, die **freie Netzkapazität** oder **verbindliche Anschlusszusage** implizieren (Hinweisbanner + serverseitige Stichwortprüfung).

## API (MVP)

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/v1/vnb/comms/threads` | Thread-Liste (Austausch-Board) |
| POST | `/api/v1/vnb/comms/threads` | Neuer Thread inkl. erster Nachricht |
| GET | `/api/v1/vnb/comms/threads/{id}` | Thread inkl. Nachrichten |
| POST | `/api/v1/vnb/comms/threads/{id}/messages` | Antwort im Thread |

## Rechtlicher Hinweis (UI)

Vorläufiger fachlicher Austausch unter Netzbetreibern. Keine Kapazitätsgarantie, keine Netzanschlusszusage. Öffentliche oder projektbezogene Personendaten nur mit dokumentierter Rechtsgrundlage.

## Roadmap

1. Org-Level-Accounts und regionale Boards
2. Anhänge (PDF, strukturierte Meldungen)
3. Moderation / Meldewesen
4. Optional: SSE/WebSocket für Live-Updates
