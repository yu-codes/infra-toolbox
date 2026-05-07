---
description: Run quality gate checks — format, lint, type-check, test, and security scan.
argument-hint: [path|.] [--fix] [--strict]
---

# Quality Gate

Run the full quality pipeline on demand.

## Usage

`/quality-gate [path|.] [--fix] [--strict]`

## Pipeline

### 1. Format Check
```bash
# Python
ruff format --check .
# Vue/TS
npx prettier --check "src/**/*.{ts,vue}"
```

### 2. Lint
```bash
# Python
ruff check .
# Vue/TS
npx eslint . --ext .ts,.vue
```

### 3. Type Check
```bash
# Python
mypy app/ --ignore-missing-imports
# TypeScript
npx tsc --noEmit
```

### 4. Test
```bash
# Python
pytest --tb=short -q
# Vue
npx vitest run
```

### 5. Security
```bash
# Python
bandit -r app/ -q
# Node
npm audit --audit-level=high
```

## Report Format

```
Quality Gate Results
────────────────────
Format:     ✅ PASS
Lint:       ✅ PASS (0 errors, 2 warnings)
Type Check: ⚠️  WARN (1 issue)
Tests:      ✅ PASS (42 passed, 0 failed)
Security:   ✅ PASS (no vulnerabilities)
────────────────────
Overall:    ✅ PASS
```

## Options

- `--fix`: Auto-format and auto-fix lint issues where possible
- `--strict`: Fail on warnings (not just errors)

## When to Use

- Before committing code
- Before opening a PR
- After completing a feature
- As a pre-push sanity check
