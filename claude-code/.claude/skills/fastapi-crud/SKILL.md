# Skill: fastapi-crud

Generate a complete CRUD endpoint set for a FastAPI resource.

## Steps

1. Define the Pydantic schema (Create, Update, Response models)
2. Create the SQLAlchemy model (if ORM is in use)
3. Write the router with all 5 endpoints:
   - `GET /items` — list with pagination
   - `GET /items/{id}` — single item
   - `POST /items` — create
   - `PUT /items/{id}` — full update
   - `DELETE /items/{id}` — delete
4. Add dependency injection for DB session
5. Return appropriate HTTP status codes

## File Layout

```
app/
  models/item.py        # SQLAlchemy model
  schemas/item.py       # Pydantic schemas
  routers/items.py      # FastAPI router
  crud/items.py         # DB operations (optional layer)
```

## Rules

- Use `async def` for all route handlers
- Use `HTTPException` for error responses
- No business logic in routers — delegate to crud layer
- Always validate input via Pydantic
