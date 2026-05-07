---
description: Python code review with PEP 8, type hints, FastAPI patterns, and security focus.
argument-hint: [file-path | blank for all changed .py files]
---

# Python Review

Focused Python code review applying PEP 8, typing, security, and FastAPI best practices.

## Process

1. Identify Python files to review:
   ```bash
   git diff --name-only -- '*.py'
   ```
2. Run static analysis:
   ```bash
   ruff check .
   mypy . --ignore-missing-imports
   ```
3. Review each file for the checklist below
4. Report findings by severity

## Checklist

### CRITICAL
- [ ] No hardcoded secrets
- [ ] No SQL injection (f-strings in queries)
- [ ] No `eval()`/`exec()` with user input
- [ ] No bare `except: pass`
- [ ] Auth checks on all protected endpoints

### HIGH
- [ ] Type hints on all public functions
- [ ] Pydantic models for request/response
- [ ] No blocking calls in async handlers
- [ ] Proper error handling (specific exceptions)
- [ ] No N+1 queries

### MEDIUM
- [ ] PEP 8 naming conventions
- [ ] Import order (stdlib → third-party → local)
- [ ] Docstrings on public functions
- [ ] No `print()` (use `logging`)
- [ ] No mutable default arguments

## Output

Report findings as:
```
[SEVERITY] Issue
File: path.py:line
Fix: Suggested change
```
