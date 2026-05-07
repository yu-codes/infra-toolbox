---
description: Analyze test coverage and identify untested code paths.
argument-hint: [path | blank for full project]
---

# Test Coverage

Analyze test coverage and identify code paths that need tests.

## Process

### 1. Run Coverage

```bash
# Python
pytest --cov=app --cov-report=term-missing --cov-report=html

# Vue/TypeScript
npx vitest run --coverage
```

### 2. Analyze Results

Report:
- Overall coverage percentage
- Files below 80% threshold
- Uncovered lines (from `term-missing`)
- Critical uncovered paths (error handling, auth, validation)

### 3. Prioritize

Rank uncovered code by risk:

| Priority | What | Why |
|----------|------|-----|
| CRITICAL | Auth, payment, data mutation | Security & correctness |
| HIGH | API endpoints, business logic | Core functionality |
| MEDIUM | Utility functions, helpers | Maintenance |
| LOW | Config, constants, types | Low risk |

### 4. Suggest Tests

For each high-priority uncovered path, suggest a test:
```python
# Suggested test for uncovered path at app/services/payment.py:45
async def test_payment_handles_timeout():
    """Line 45: except TimeoutError branch is untested."""
    with mock.patch("httpx.AsyncClient.post", side_effect=TimeoutError):
        result = await process_payment(amount=100)
        assert result.status == "failed"
```

## Target

- Minimum: 80% line coverage
- Ideal: 90%+ for critical paths (auth, payments, data)
- Acceptable: 60%+ for UI components

## Output

```
Coverage Report
───────────────
Overall:        78% (target: 80%)
Backend (app/): 82% ✅
Frontend (src/): 71% ⚠️

Files Below Threshold:
  app/services/payment.py    62% (CRITICAL — payment logic)
  app/routers/auth.py        69% (CRITICAL — auth logic)
  src/views/Dashboard.vue    55% (MEDIUM — UI)

Suggested: 5 tests to reach 80% overall
```
