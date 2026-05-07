# Project CLAUDE.md Template

> 複製此檔案到你的專案根目錄並根據實際情況修改。

## Project Overview

Stack: Python 3.12+, FastAPI, PostgreSQL, Docker Compose
Frontend: Vue 3 + TypeScript + Vite + Pinia
Architecture: [描述你的架構]

## Critical Rules

- Async route handlers only
- Pydantic v2 for all schemas
- Business logic in service layer, not routers
- All endpoints must have tests
- Docker Compose for local development

## File Structure

```
backend/
  app/
    main.py
    core/         # Config, deps, exceptions
    models/       # ORM models
    schemas/      # Pydantic schemas
    routers/      # API endpoints
    services/     # Business logic
  tests/
  Dockerfile
  requirements.txt

frontend/
  src/
    components/
    composables/
    views/
    stores/
    router/
  tests/
  Dockerfile

docker-compose.yml
```

## Environment Variables

```
# Backend
DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/myapp
REDIS_URL=redis://redis:6379/0
SECRET_KEY=change-me
DEBUG=true

# Frontend
VITE_API_BASE_URL=http://localhost:8000
```

## Development Commands

```bash
# Start all services
docker compose up -d

# Run backend tests
docker compose exec backend pytest --cov=app

# Run frontend tests
cd frontend && pnpm test

# Lint & format
ruff check app/ --fix
ruff format app/
```

## Git Workflow

- `feat:` new features, `fix:` bug fixes, `refactor:` code changes
- Feature branches from `main`, PRs required
- CI: ruff (lint + format), pytest (tests), vitest (frontend tests)
