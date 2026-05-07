---
name: api-design
description: REST API design patterns for FastAPI. Use when creating new endpoints, designing request/response schemas, or structuring API routes.
---

# API Design Patterns (FastAPI)

## Endpoint Structure

```python
# app/routers/{resource}.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.schemas.items import ItemCreate, ItemUpdate, ItemResponse, ItemListResponse
from app.services.items import ItemService
from app.dependencies import get_current_user, get_db

router = APIRouter(prefix="/api/items", tags=["items"])

@router.get("", response_model=ItemListResponse)
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """List items with pagination."""
    items, total = await ItemService(db).list(user_id=user.id, skip=skip, limit=limit)
    return ItemListResponse(items=items, total=total, skip=skip, limit=limit)

@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    payload: ItemCreate,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """Create a new item."""
    return await ItemService(db).create(user_id=user.id, data=payload)

@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: int,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """Get item by ID."""
    item = await ItemService(db).get(item_id)
    if not item or item.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@router.patch("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: int,
    payload: ItemUpdate,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """Partial update item."""
    return await ItemService(db).update(item_id, user_id=user.id, data=payload)

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: int,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """Delete item."""
    await ItemService(db).delete(item_id, user_id=user.id)
```

## Schema Design (Pydantic v2)

```python
# app/schemas/items.py
from pydantic import BaseModel, Field, ConfigDict

class ItemBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    price: float = Field(gt=0, le=99999.99)

class ItemCreate(ItemBase):
    pass

class ItemUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    price: float | None = Field(None, gt=0, le=99999.99)

class ItemResponse(ItemBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    owner_id: int
    created_at: datetime

class ItemListResponse(BaseModel):
    items: list[ItemResponse]
    total: int
    skip: int
    limit: int
```

## Error Responses

```python
# Consistent error format
{
    "detail": "Item not found",
    "code": "ITEM_NOT_FOUND",
    "status": 404
}
```

## Pagination Pattern

Always use offset/limit with total count:
- `GET /api/items?skip=0&limit=20` → `{ items: [...], total: 150, skip: 0, limit: 20 }`

## Naming Conventions

| Resource | Endpoint | Method |
|----------|----------|--------|
| List | `/api/items` | GET |
| Create | `/api/items` | POST |
| Read | `/api/items/{id}` | GET |
| Update | `/api/items/{id}` | PATCH |
| Delete | `/api/items/{id}` | DELETE |
| Action | `/api/items/{id}/publish` | POST |

## Rules

- Always use `response_model` for type safety
- Always validate input with Pydantic schemas
- Use service layer (not business logic in routes)
- Return proper HTTP status codes
- Use `Depends()` for auth, DB, and shared logic
