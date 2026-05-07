# Python / FastAPI Rules

## Code Style

- Type hints on ALL function signatures — use `from __future__ import annotations`
- No `print()` statements — use `logging.getLogger(__name__)`
- f-strings for string formatting, never `%` or `.format()`
- Use `pathlib.Path` not `os.path` for file operations
- Imports sorted: stdlib → third-party → local (enforced by ruff)
- Max line length: 120 characters

## FastAPI Conventions

- Async route handlers only (`async def`)
- Pydantic v2 for all schemas (BaseModel with model_config)
- Dependency injection via `Depends()`
- `HTTPException` for all error responses
- No business logic in route handlers — delegate to service layer
- Use `APIRouter` for route grouping by domain
- Always return explicit status codes

## Project Structure

```
app/
  main.py              # FastAPI app initialization
  core/
    config.py          # Settings via pydantic-settings
    deps.py            # Shared dependencies
    exceptions.py      # Custom exception handlers
  models/              # SQLAlchemy / ORM models
  schemas/             # Pydantic request/response schemas
  routers/             # API route handlers
  services/            # Business logic layer
  tests/
    conftest.py        # Shared fixtures
    test_*.py          # Test files
```

## Database

- Use async SQLAlchemy or async database driver
- Migrations committed to git (Alembic)
- Parameterized queries only — never raw string interpolation
- Use `select_related` patterns to prevent N+1 queries
- All models must have `created_at` and `updated_at` fields
- Indexes on fields used in `filter()` or `WHERE` clauses

## Error Handling

```python
from fastapi import HTTPException, status

# Service layer raises domain exceptions
class InsufficientStockError(Exception):
    pass

# Router translates to HTTP
@router.post("/orders", status_code=status.HTTP_201_CREATED)
async def create_order(data: CreateOrderSchema, db=Depends(get_db)):
    try:
        return await order_service.create(db, data)
    except InsufficientStockError:
        raise HTTPException(status_code=409, detail="Insufficient stock")
```

## Testing

- Use `pytest` + `pytest-asyncio` + `httpx.AsyncClient`
- Fixtures in `conftest.py` for DB session, test client
- Factory pattern for test data (factory-boy or manual)
- Test both happy path and error cases

## Docker

- Use `python:3.12-slim` as base image
- Multi-stage build: builder → runtime
- Run as non-root user
- Use `uvicorn` with `--workers` in production
- Health check endpoint at `/health`
