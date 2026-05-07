---
description: Safely identify and remove dead code with verification after each change.
---

# Refactor Clean

Safely identify and remove dead code with test verification at every step.

## Step 1: Detect Dead Code

| Tool | What It Finds | Command |
|------|--------------|---------|
| vulture | Unused Python code | `vulture app/ --min-confidence 80` |
| ruff | Unused imports | `ruff check . --select F401` |
| knip | Unused exports, files, deps | `npx knip` |
| depcheck | Unused npm dependencies | `npx depcheck` |

## Step 2: Categorize Findings

| Tier | Examples | Action |
|------|----------|--------|
| **SAFE** | Unused utilities, internal functions | Delete with confidence |
| **CAUTION** | Routes, middleware, components | Verify no dynamic imports |
| **DANGER** | Config files, entry points, types | Investigate first |

## Step 3: Safe Deletion Loop

For each SAFE item:
1. **Run full test suite** — Establish baseline
2. **Delete the dead code**
3. **Re-run test suite** — Verify nothing broke
4. **If tests fail** — Immediately revert (`git checkout -- <file>`)
5. **If tests pass** — Move to next item

## Step 4: Consolidate Duplicates

After removing dead code:
- Near-duplicate functions (>80% similar) → merge into one
- Redundant type definitions → consolidate
- Wrapper functions that add no value → inline
- Re-exports that serve no purpose → remove

## Step 5: Summary

```
Dead Code Cleanup
──────────────────────────────
Deleted:   X unused functions
           X unused files
           X unused dependencies
Skipped:   X items (tests failed)
Saved:     ~X lines removed
──────────────────────────────
All tests passing ✅
```

## Rules

- **Never delete without running tests first**
- **One deletion at a time** — Atomic changes
- **Skip if uncertain** — Better to keep dead code than break production
- **Don't refactor while cleaning** — Separate concerns
