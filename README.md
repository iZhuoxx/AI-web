# AI Toolbox

AI-powered study assistant built with Vue 3 + Vite (frontend) and FastAPI (backend). It supports file uploads, vector search, and audio transcription to help you organize and generate knowledge quickly.

## Stack & Layout
- `web/`: Vue 3 + TypeScript + Vite (Ant Design Vue UI)
- `api/`: FastAPI, SQLAlchemy, Alembic, S3/audio workflows
- `docker-compose.yml`: PostgreSQL 16 (Redis optional)

## Prerequisites
- Node.js ≥ 18 (pnpm or npm/yarn)
- Python ≥ 3.10 (pip or poetry)
- PostgreSQL and Redis (can be started via `docker compose`)

## Quick Start (Dev)
1) Start databases  
```bash
docker compose up -d postgres
```

2) Backend env: copy `api/.env.example` if present (or create `api/.env`) and fill:  
```env
DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/aiweb
JWT_SECRET_KEY=your-long-random-secret
CSRF_SECRET=another-random-secret
SESSION_COOKIE_SECURE=false
SESSION_COOKIE_SAMESITE=lax
AWS_S3_BUCKET=your-bucket
AWS_S3_REGION=ap-northeast-1
AWS_S3_ENDPOINT_URL=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
```

3) Install deps  
```bash
cd web && pnpm install
cd ../api && pip install -r requirements.txt
```

4) Init database (first time)  
```bash
cd api
alembic upgrade head
```

5) Run dev servers (two terminals)  
```bash
# Backend: FastAPI with reload
cd api
python3 -m uvicorn api.app:app --reload --host 0.0.0.0 --port 8000

# Frontend: Vite dev server with /api proxy
cd web
pnpm run dev  # http://localhost:5173
```

## Production
```bash
# Build frontend assets
cd web && pnpm build

# Serve frontend via FastAPI
cd ../api
SERVE_SPA=true uvicorn api.app:app --host 0.0.0.0 --port 8000
```
Use systemd/supervisor to keep the process running and place a TLS reverse proxy in front.

## Database & Migrations
- Migration scripts live in `api/alembic/versions`.
- First-time setup: run `cd api && alembic upgrade head` to create all tables.
- Create migration (after changing models): `cd api && alembic revision --autogenerate -m "describe change"`
- Apply latest migration: `alembic upgrade head` (or target a revision hash; roll back with `alembic downgrade <rev>`).
- Handy psql: `\dt` list tables, `\d <table>` describe, `\l` list DBs, `\q` quit.

## Frontend Config
- Default API proxy: `http://localhost:8000/api`. Override in `web/.env.development` with `VITE_API_BASE_URL=https://your-api.com/api`.
- Streaming/transcription endpoints can also be set there: `VITE_RESPONSES_ENDPOINT`, `VITE_TRANSCRIBE_STREAM_ENDPOINT`, `VITE_TRANSCRIBE_REALTIME_WS`.
