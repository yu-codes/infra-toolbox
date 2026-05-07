# Testing Requirements

## Minimum Test Coverage: 80%

Test Types (ALL required for production features):
1. **Unit Tests** — Individual functions, utilities, components
2. **Integration Tests** — API endpoints, database operations
3. **E2E Tests** — Critical user flows (when applicable)

## Test-Driven Development

MANDATORY workflow:
1. Write test first (RED)
2. Run test — it should FAIL
3. Write minimal implementation (GREEN)
4. Run test — it should PASS
5. Refactor (IMPROVE)
6. Verify coverage (80%+)

## Test Structure (AAA Pattern)

```python
def test_create_order_success():
    # Arrange
    product = create_product(price=100, stock=10)
    
    # Act
    order = create_order(product_id=product.id, quantity=2)
    
    # Assert
    assert order.total == 200
    assert product.stock == 8
```

## Test Naming

Use descriptive names that explain the behavior under test:
- `test_returns_empty_list_when_no_items_match_query`
- `test_raises_error_when_api_key_missing`
- `test_creates_user_with_hashed_password`

## Tools

- **Python**: pytest + pytest-cov + pytest-asyncio + httpx (for FastAPI)
- **Vue**: vitest + @vue/test-utils + happy-dom

## Rules

- Test behavior, not implementation
- One assertion per test when possible
- Never skip the failing step in TDD
- Mock external services, not internal logic
