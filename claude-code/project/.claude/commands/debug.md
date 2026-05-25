---
description: Structured debugging workflow — Reproduce, Isolate, Diagnose, Fix, Verify. Use when something is broken and you're not sure why.
argument-hint: "<error message or description of the problem>"
---

# Debug Workflow

Systematic 5-step debugging process. Do not guess — investigate first.

## Workflow

### Step 1: REPRODUCE
Confirm the error is real and understand its exact conditions.

```bash
# Check recent logs
docker compose logs --tail=50 <service>

# Run the failing test in isolation
pytest tests/test_xxx.py::test_specific -xvs    # Python
npx vitest run src/path/to/spec.ts              # TypeScript

# Check process/port status
docker compose ps
curl -v http://localhost:PORT/health
```

Questions to answer:
- Does the error reproduce consistently?
- What exact input/state triggers it?
- Does it happen in all environments or only specific ones?

### Step 2: ISOLATE
Narrow down where the problem is.

```bash
# Find relevant files
grep -r "ErrorClass\|error message keyword" . --include="*.py" -l
grep -r "ErrorClass\|error message keyword" . --include="*.ts" -l

# Check recent changes
git log --oneline -10
git diff HEAD~1 -- <relevant file>

# Check dependencies
pip show <package>   # Python
npm list <package>   # Node
```

Questions to answer:
- Which layer is failing? (DB, service, API, frontend, network?)
- Was this working before? When did it break?
- What changed recently?

### Step 3: DIAGNOSE
Read the root cause, not just the symptom.

- Read the FULL stack trace — the root cause is usually at the bottom, not the top
- Read the failing code and its dependencies
- Check for: type mismatches, null/undefined, async/await missing, env var missing, wrong port/URL, DB schema mismatch

Common root causes by symptom:

| Symptom | Common Root Cause |
|---------|-------------------|
| `404 Not Found` | Route not registered, wrong prefix, wrong method |
| `422 Unprocessable Entity` | Pydantic schema mismatch, missing required field |
| `500 Internal Server Error` | Unhandled exception, check logs for traceback |
| `Connection refused` | Service not started, wrong port, Docker network issue |
| `CORS error` | Missing CORS middleware, wrong allowed origins |
| `TypeError: undefined` | Missing await, null not handled, wrong key name |
| `Migration error` | Schema drift, applied out of order, env mismatch |
| `Test passes locally, fails in CI` | Env var missing, order dependency, timezone issue |

### Step 4: FIX
Apply the minimal fix that addresses the root cause.

- Fix root cause, not symptoms
- Do not add workarounds for problems you don't understand
- Use the tdd-workflow: write a regression test first, then fix

### Step 5: VERIFY
Confirm the fix works and nothing else broke.

```bash
# Re-run the failing test
pytest tests/test_xxx.py -xvs

# Run full test suite
pytest --tb=short -q

# Check no regressions
/quality-gate
```

## Output Format

```
Debug Report
────────────
Symptom: <what the user reported>
Reproduced: YES / NO

Root Cause:
  File: path/to/file.py:42
  Cause: <1-2 sentence explanation>

Fix Applied:
  <description of change>

Verification:
  Tests: PASS (N passed)
  Regression check: PASS
```

## Rules

- Read before fixing — understand the code before changing it
- One hypothesis at a time — test each theory before moving to the next
- If stuck after 3 hypotheses, use `/plan` to step back and rethink
- If it's an external service issue (DB down, API rate limit), escalate instead of code-fixing
