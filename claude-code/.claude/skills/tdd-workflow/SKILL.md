# Skill: tdd-workflow

Apply red-green-refactor TDD cycle to any function or feature.

## Steps

### Red — Write a failing test
1. Identify the smallest testable unit
2. Write one test that calls the function with expected input/output
3. Run the test — confirm it fails

### Green — Make it pass
4. Write the minimum code to pass the test
5. Run the test — confirm it passes

### Refactor
6. Clean up code without changing behavior
7. Re-run tests — still green

### Repeat
8. Add next test for edge case or next behavior
9. Repeat from step 1

## Python (pytest)

```python
# tests/test_items.py
def test_create_item_returns_id():
    result = create_item({"name": "test"})
    assert result["id"] is not None
```

## Vue (vitest)

```ts
// components/__tests__/MyComponent.spec.ts
import { mount } from '@vue/test-utils'
import MyComponent from '../MyComponent.vue'

test('renders label', () => {
  const wrapper = mount(MyComponent, { props: { label: 'Hello' } })
  expect(wrapper.text()).toContain('Hello')
})
```

## Rules

- One assertion per test when possible
- Test behavior, not implementation
- Never skip the failing step
