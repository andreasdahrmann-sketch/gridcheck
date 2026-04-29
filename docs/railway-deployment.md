# GridCheck – Railway Deployment

## Übersicht
GridCheck läuft auf Railway mit zwei Services:
- **backend** – FastAPI (Python)
- **frontend** – Next.js

## Voraussetzungen
- Railway CLI installiert
- PostgreSQL 16 als Railway Plugin
- Umgebungsvariablen gesetzt

## Umgebungsvariablen

### Backend
\\\
DATABASE_URL=postgresql://...
SECRET_KEY=...
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
CORS_ORIGINS=https://your-frontend.railway.app
\\\

### Frontend
\\\
NEXT_PUBLIC_API_URL=https://your-backend.railway.app
\\\

## Deployment

### Backend
\\\ash
cd backend
railway up
\\\

### Frontend
\\\ash
cd frontend
railway up
\\\

## Datenbank-Migration
\\\ash
cd backend
alembic upgrade head
\\\

## Health Check
- Backend: GET /health
- Frontend: GET /

## Wichtige Hinweise
- Kein SQLite in Produktion
- Secrets NIEMALS im Code
- Logs: strukturiert (JSON)
- Soft-Delete: kein hartes DELETE
