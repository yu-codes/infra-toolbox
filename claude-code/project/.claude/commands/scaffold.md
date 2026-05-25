---
description: Scaffold a new FastAPI + Vue service — generates project structure, Docker setup, env config, and README.
argument-hint: "<service name and brief description>" e.g. "task-api: task management with JWT auth"
---

# Scaffold New Service

Bootstrap a complete, runnable FastAPI + PostgreSQL + Vue service.

## What This Command Does

1. **Generate structure** — Backend (FastAPI) + Frontend (Vue 3) directory layout
2. **Docker setup** — `docker-compose.yml`, `Dockerfile` for both services, `.dockerignore`
3. **Environment config** — `.env.example` with all required variables documented
4. **Boilerplate** — `main.py`, `config.py`, `database.py`, `conftest.py`, Vue entry files
5. **README** — Quick-start instructions

## Generated Structure

```
<service-name>/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + /health endpoint
│   │   ├── core/
│   │   │   ├── config.py        # pydantic-settings
│   │   │   └── deps.py          # Shared dependencies (DB, auth)
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic v2 request/response schemas
│   │   ├── routers/             # API route handlers
│   │   └── services/            # Business logic
│   ├── tests/
│   │   └── conftest.py          # pytest fixtures (async client, DB session)
│   ├── alembic/
│   │   └── versions/
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── composables/
│   │   ├── views/
│   │   ├── stores/
│   │   └── router/
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```

## Output Format

```
Scaffolding: <service name>
─────────────────────────
Created: [list of files]

Next steps:
  1. cd <service-name>/
  2. cp .env.example .env
  3. docker compose up -d
  4. docker compose exec backend alembic upgrade head
  5. curl http://localhost:8000/health
```

## Rules

- Always generate `.env.example` — never `.env`
- Always include `GET /health` endpoint
- Follow `docker-patterns` skill for Dockerfiles (multi-stage, non-root user)
- Follow `api-design` skill for endpoint structure
- Include `conftest.py` with async test client and DB fixtures
