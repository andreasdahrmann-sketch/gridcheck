# GRIDCHECK — Architekturentscheidungen

## 1. KEIN Supabase (bewusster Bruch mit .cursorrules-Default)
Grund: Revisionssicherheit (GoBD) + volle Datenhoheit.
Cloud-Dienste sind ausgeschlossen.

## 2. Docker = Supabase-Ersatz (lokal)
- gridcheck-postgres : postgis/postgis:16-3.4, Port 5433
- gridcheck-redis    : redis:7-alpine, Port 6379
- Volume: gridcheck-pgdata (persistent)
- Compose: C:\Users\andre\gridcheck\docker-compose.yml

## 3. Revisionskette (Audit-Layer)
daten/revisionen.jsonl, SHA-256 Hash-Chain.
Bleibt bestehen AUCH nach Postgres-Migration (Audit ueber DB).

## 4. Aktueller Stand
- Engine v2 + API v2: laufen JSONL-basiert
- Postgres-Container: laeuft, aber von Engine NOCH NICHT genutzt
- Migration JSONL -> Postgres: geplanter Meilenstein

## 5. Regel
Docker Desktop MUSS laufen, bevor Backend gestartet wird
(sobald Postgres-Anbindung aktiv ist).
