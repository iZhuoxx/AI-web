# AI Web API Backend

This backend now supports PostgreSQL storage via SQLAlchemy + Alembic, email/password authentication, secure cookies, CSRF protection, note management, and S3-backed attachments.

## 1. Environment setup

1. Install dependencies:

   ```bash
   cd api
   pip install -r requirements.txt
   # or: poetry install
   ```

2. Copy `.env` and fill in the following keys:

   ```env
   DATABASE_URL=postgresql+psycopg://noteai:password@localhost:5432/appdb
   JWT_SECRET_KEY=your-very-long-random-secret
   CSRF_SECRET=another-random-secret
   SESSION_COOKIE_SECURE=false        # true in production over HTTPS
   SESSION_COOKIE_SAMESITE=lax
   AWS_S3_BUCKET=your-bucket
   AWS_S3_REGION=ap-northeast-1
   AWS_S3_ENDPOINT_URL=optional-custom-endpoint
   AWS_ACCESS_KEY_ID=...              # or leave empty to read from s3-easylearn-user_accessKeys.csv
   AWS_SECRET_ACCESS_KEY=...
   ```

   The `.csv` file in this folder is parsed automatically when explicit access keys are not provided.

3. Optional dev toggles:

   - `SQLALCHEMY_ECHO=true` to log SQL.
   - `SQLALCHEMY_DISABLE_POOL=true` if running Alembic while uvicorn reloads.

## 2. Database migrations

1. Ensure PostgreSQL is running (the provided `docker-compose.yml` exposes port `5432`).
2. Apply the initial schema:

   ```bash
   cd api
   alembic upgrade head
   ```

3. To create subsequent migrations after model changes:

   ```bash
   alembic revision --autogenerate -m "describe change"
   alembic upgrade head
   ```

## 3. Running the API

```bash
uvicorn api.app:app --reload --host 0.0.0.0 --port 8000
```

New REST endpoints (all prefixed with `/api`):

- `GET /auth/csrf` – issues a CSRF token cookie/JSON payload.
- `POST /auth/register` – email registration (requires CSRF header).
- `POST /auth/login` / `POST /auth/logout`.
- `GET /auth/me` – session info with memberships.
- `GET|POST|PUT|DELETE /notebooks` – CRUD for user notebooks (each contains multiple notes).
- `POST /notebooks/{notebook_id}/messages` – append chat entries to a notebook.
- `POST /attachments/presign-upload` – returns S3 form data and creates an attachment row.
- `GET /attachments/{attachment_id}/download-url` – presigned download links.

All mutating requests must include `X-CSRF-Token` that matches the `csrf_token` cookie, and requests should always be sent with `credentials: 'include'` so the HttpOnly session cookie works.

## 4. Frontend follow-up

See `web/frontend_auth_notes.md` for the Vue integration checklist covering API wiring, sidebar UI, and CSRF handling.
