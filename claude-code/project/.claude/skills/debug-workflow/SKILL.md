---
name: debug-workflow
description: Structured debugging skill — Reproduce, Isolate, Diagnose, Fix, Verify. Use when something is broken and root cause is unclear.
version: 1.0.0
tags: [debugging, troubleshooting, backend, frontend]
---

# Debug Workflow

Follow this 5-step process. Do not skip steps or guess.

## Rule: Read Before Fix

Before touching any code:
1. Read the full error message and stack trace
2. Read the code at the failing line
3. Read what calls the failing code
4. Form ONE hypothesis, then test it

## Step 1: REPRODUCE

Confirm the error with a minimal reproduction.

```bash
# Backend
pytest tests/test_xxx.py::test_failing -xvs
docker compose logs --tail=100 api | grep -i error

# Frontend
npx vitest run src/path/to/spec.ts --reporter=verbose

# HTTP
curl -v -X POST http://localhost:8000/api/endpoint \
  -H "Content-Type: application/json" \
  -d '{"field": "value"}'
```

If it doesn't reproduce: check environment (env vars, DB state, order of operations).

## Step 2: ISOLATE

Find the exact boundary where the failure occurs.

```bash
# What changed recently?
git log --oneline -10
git diff HEAD~3 -- src/affected/path

# Search for the error keyword
grep -r "ErrorMessage\|failing_function" . --include="*.py" -n
grep -r "ErrorMessage\|failing_function" . --include="*.ts" -n

# Check dependencies
pip show package-name
npm list package-name
docker compose ps
```

Layer checklist (eliminate one by one):
- [ ] Database: is it up? schema matches?
- [ ] Environment: are all required env vars set?
- [ ] Network: can the service reach its dependencies?
- [ ] Code logic: is the algorithm correct?
- [ ] Input data: is the data in the expected shape?
- [ ] Types: are types/schemas aligned across layers?

## Step 3: DIAGNOSE

Read the root cause from the full stack trace, not just the top line.

Common patterns:

| Error | Likely Cause |
|-------|-------------|
| `AttributeError: NoneType` | Missing null check, awaited value not returned |
| `KeyError` / `undefined` | Wrong key name, different API response shape than expected |
| `ValidationError` | Schema mismatch — check field names and types |
| `IntegrityError` | DB constraint violation — duplicate key, null in NOT NULL column |
| `ECONNREFUSED` | Service not running, wrong port, Docker network not created |
| `401 Unauthorized` | Token expired, wrong auth header format |
| `403 Forbidden` | Permission check failing, wrong user context |
| `CORS` blocked | Missing CORS middleware, wrong allowed origin |
| `Hydration mismatch` (React) | Server/client rendered different HTML — check conditional rendering |
| `Cannot read properties of undefined` | async data used before loaded, missing optional chaining |

Write your diagnosis as one sentence: _"The root cause is X in file Y:line Z because..."_

## Step 4: FIX

Apply the minimum change to fix the root cause.

- Write a regression test FIRST (so you know exactly when it's fixed)
- Then implement the fix
- Do not fix symptoms — fix the root cause
- Do not add `try/except` to hide errors you don't understand

```python
# BAD: hiding the problem
try:
    result = do_thing()
except Exception:
    return None

# GOOD: fix the actual cause, handle explicitly
if not prerequisite:
    raise ValueError("prerequisite missing")
result = do_thing()
```

## Step 5: VERIFY

```bash
# 1. The specific test passes
pytest tests/test_xxx.py -xvs

# 2. Full suite still passes
pytest --tb=short -q

# 3. No type errors introduced
mypy app/ --ignore-missing-imports
npx tsc --noEmit

# 4. Run the quality gate
/quality-gate
```

## When to Escalate (Stop Debugging, Ask Instead)

- Spent 3+ iterations without progress → step back with `/plan`
- The bug is in a dependency, not your code → check issue tracker / changelog
- The bug requires data migration → plan a migration strategy first
- The system behavior is ambiguous → clarify requirements before fixing
