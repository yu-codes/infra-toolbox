---
description: Detect the project build system and incrementally fix build/type errors with minimal safe changes.
---

# Build Fix

Incrementally fix build and type errors with minimal, safe changes.

## Step 1: Detect Build System

| Indicator | Build Command |
|-----------|---------------|
| `pyproject.toml` / `setup.py` | `python -m compileall -q .` then `mypy .` |
| `requirements.txt` | `pip install -r requirements.txt` then check imports |
| `package.json` with `build` | `npm run build` |
| `tsconfig.json` | `npx tsc --noEmit` |
| `docker-compose.yml` | `docker compose build` |
| `Dockerfile` | `docker build .` |

## Step 2: Parse and Group Errors

1. Run the build command and capture stderr
2. Group errors by file path
3. Sort by dependency order (fix imports before logic errors)
4. Count total errors for progress tracking

## Step 3: Fix Loop (One Error at a Time)

For each error:
1. **Read the file** — 10 lines around the error
2. **Diagnose** — Missing import, wrong type, syntax error
3. **Fix minimally** — Smallest change that resolves the error
4. **Re-run build** — Verify error is gone and no new errors
5. **Move to next**

## Step 4: Guardrails

Stop and ask if:
- A fix introduces more errors than it resolves
- Same error persists after 3 attempts
- Fix requires architectural changes
- Missing dependencies need user decision

## Step 5: Summary

```
Build Fix Results
─────────────────
Errors fixed:     5 (with file paths)
Errors remaining: 0
New errors:       0
Status:           ✅ BUILD PASSING
```

## Recovery Strategies

| Situation | Action |
|-----------|--------|
| Missing module (Python) | `pip install <package>` or fix import |
| Missing module (Node) | `npm install <package>` |
| Type mismatch | Fix annotation or add type cast |
| Circular dependency | Identify cycle; extract shared module |
| Docker build fail | Check COPY paths, base image, build context |

Fix one error at a time. Prefer minimal diffs over refactoring.
