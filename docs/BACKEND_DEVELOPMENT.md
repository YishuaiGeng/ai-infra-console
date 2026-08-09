# Backend Development

The Central API is implemented in `apps/api` with FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis, and RQ.

## Requirements

- Python 3.11 or newer
- `uv` 0.9 or newer
- Docker Engine with Compose v2 for the full stack

## Install

```bash
uv sync --project apps/api --all-groups --frozen
```

Run the API checks:

```bash
npm run check:api
```

## Local infrastructure

Create a local environment file from `.env.example` and replace every placeholder before using production mode. Do not commit `.env`.

Start the complete stack:

```bash
docker compose up -d --build
docker compose ps
```

Default development URLs:

- Web console: `http://localhost:3000`
- API liveness: `http://localhost:8000/health/live`
- API readiness: `http://localhost:8000/health/ready`
- Swagger UI: `http://localhost:8000/docs`

Swagger and OpenAPI routes are disabled when `AI_INFRA_ENVIRONMENT=production`.

## Database migrations

The API container runs `alembic upgrade head` before starting. For an externally available database, run:

```bash
AI_INFRA_DATABASE_URL=postgresql+asyncpg://user:password@host/database npm run api:migrate
```

Create a migration after changing SQLAlchemy metadata:

```bash
uv run --project apps/api alembic -c apps/api/alembic.ini revision --autogenerate -m "describe change"
```

Always inspect generated migrations and test upgrade, downgrade, and re-upgrade before committing.

## Authentication bootstrap

The first administrator is created from:

- `AI_INFRA_BOOTSTRAP_ADMIN_USERNAME`
- `AI_INFRA_BOOTSTRAP_ADMIN_PASSWORD`

The password is Argon2-hashed before storage and is never logged. Bootstrap is idempotent: it does not overwrite an existing user.

Login:

```http
POST /api/v1/auth/login
Content-Type: application/json

{"username":"admin","password":"your-password"}
```

Use the returned token as `Authorization: Bearer <token>` when calling `/api/v1/auth/me` or the authenticated API index.

## Error format

Every API error returns the same envelope and the response contains the same `X-Request-ID`:

```json
{
  "error": {
    "code": "invalid_credentials",
    "message": "The username or password is incorrect.",
    "request_id": "019fd...",
    "details": null
  }
}
```

Unexpected exceptions are logged server-side and sanitized in client responses.

## Worker

The `worker` service listens only for registered Python task functions on the RQ queue. It does not expose shell, command, or arbitrary code execution APIs.

The Phase 1 health task is `ai_infra_api.worker.health_probe`. It exists only to verify Redis queue transport and worker processing before real jobs are added in later phases.

## Production target

The Central stack is intended for `gpu-node-01`. Host roles and mutation restrictions are documented in [Deployment Targets](./DEPLOYMENT_TARGETS.md). Keep SSH configuration, addresses, and credentials outside the repository.
