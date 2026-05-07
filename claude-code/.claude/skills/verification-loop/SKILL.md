---
name: verification-loop
description: Build-test-lint-typecheck verification loop. Run after any implementation to ensure code quality before committing.
---

# Verification Loop

Run the full verification pipeline after implementing changes. Ensures code is ready to commit.

## Pipeline

Execute in order. Stop at first failure.

### 1. Build
```bash
# Python
python -m compileall -q app/

# Vue/TypeScript
npm run build
```

### 2. Type Check
```bash
# Python
mypy app/ --ignore-missing-imports

# TypeScript
npx tsc --noEmit
```

### 3. Lint
```bash
# Python
ruff check app/ tests/

# Vue/TS
npx eslint . --ext .ts,.vue --max-warnings 0
```

### 4. Format
```bash
# Python
ruff format --check app/ tests/

# Vue/TS
npx prettier --check "src/**/*.{ts,vue}"
```

### 5. Test
```bash
# Python
pytest --tb=short -q

# Vue
npx vitest run
```

### 6. Security
```bash
# Python
bandit -r app/ -q -ll

# Node
npm audit --audit-level=high
```

## On Failure

| Step | If Fails | Action |
|------|----------|--------|
| Build | Syntax/import error | Fix immediately |
| Type Check | Type mismatch | Add annotation or fix logic |
| Lint | Style violation | Auto-fix with `ruff check --fix` or `eslint --fix` |
| Format | Wrong format | Auto-fix with `ruff format` or `prettier --write` |
| Test | Assertion failure | Fix implementation or update test |
| Security | Vulnerability | Address per severity |

## When to Run

- After implementing a feature (before commit)
- After fixing a bug
- After refactoring
- Before opening a PR
- After merging upstream changes

## Quick Pass Check

```bash
# One-liner for Python projects
ruff format app/ && ruff check app/ --fix && mypy app/ && pytest -q

# One-liner for Vue projects
npx prettier --write src/ && npx eslint . --fix && npx tsc --noEmit && npx vitest run
```

## Success Criteria

All 6 steps must pass before committing:
```
Verification Loop
─────────────────
Build:      ✅
Type Check: ✅
Lint:       ✅
Format:     ✅
Tests:      ✅ (42 passed)
Security:   ✅
─────────────────
Ready to commit ✅
```
