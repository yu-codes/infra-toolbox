---
name: tdd-workflow
description: Test-Driven Development workflow. Use when implementing new features, fixing bugs, or when user asks to write code test-first.
---

# TDD Workflow

Enforce Red-Green-Refactor cycle for all implementations.

## When to Use

- New feature implementation
- Bug fixes (write regression test first)
- Refactoring existing code
- Any time user says "TDD", "test first", or "test-driven"

## Workflow

### Step 1: Define Interface
Before any test, clarify the function signature:
- Input types and constraints
- Output type and shape
- Side effects (DB writes, API calls)
- Error cases

### Step 2: RED — Write Failing Test

```python
# Python: tests/test_<module>.py
import pytest
from app.services.items import create_item

class TestCreateItem:
    async def test_creates_with_valid_data(self, db_session):
        result = await create_item(db_session, name="Widget", price=9.99)
        assert result.id is not None
        assert result.name == "Widget"

    async def test_rejects_negative_price(self, db_session):
        with pytest.raises(ValueError, match="price must be positive"):
            await create_item(db_session, name="Widget", price=-1)
```

```typescript
// Vue: src/components/__tests__/ItemForm.spec.ts
import { mount } from '@vue/test-utils'
import ItemForm from '../ItemForm.vue'

describe('ItemForm', () => {
  it('emits submit with form data', async () => {
    const wrapper = mount(ItemForm)
    await wrapper.find('[data-testid="name"]').setValue('Widget')
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('submit')?.[0][0]).toEqual({ name: 'Widget' })
  })
})
```

### Step 3: Run Test — Confirm FAIL

```bash
pytest tests/test_items.py -x -v        # Python
npx vitest run src/**/*.spec.ts          # Vue
```

The test MUST fail. If it passes, the test is not testing new behavior.

### Step 4: GREEN — Minimal Implementation

Write ONLY enough code to make the test pass. No extras.

### Step 5: Run Test — Confirm PASS

```bash
pytest tests/test_items.py -x -v
```

### Step 6: REFACTOR

- Remove duplication
- Improve naming
- Extract helpers if needed
- Re-run tests — must still pass

### Step 7: Repeat

Add next test for:
1. Edge case (empty input, boundary values)
2. Error case (invalid data, missing fields)
3. Integration (with database, with other services)

### Step 8: Verify Coverage

```bash
pytest --cov=app --cov-fail-under=80
```

## Rules

- ONE test at a time — never bulk generate tests
- Test BEHAVIOR, not implementation
- Never skip the failing step
- Mocks for external dependencies only
- Each test must be independent (no shared mutable state)

## Coverage Targets

| Component | Minimum |
|-----------|---------|
| Business logic | 90% |
| API endpoints | 80% |
| Utility functions | 80% |
| Vue components | 70% |
