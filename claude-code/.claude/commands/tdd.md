# /tdd

Enforce a test-driven development workflow for a given feature or function.

## Steps

1. Ask: what is the function/feature to implement?
2. Write the test first (failing)
3. Write the minimal implementation to make the test pass
4. Refactor only after tests are green
5. Repeat for edge cases

## Usage

```
/tdd <feature description>
```

## Rules

- Tests go in `tests/` (Python) or `*.spec.ts` / `*.test.ts` (Vue)
- One test at a time — no bulk test generation
- Do NOT implement logic before writing at least one test
- Use `pytest` for Python, `vitest` for Vue
