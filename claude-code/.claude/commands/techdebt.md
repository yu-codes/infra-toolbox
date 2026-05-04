# /techdebt

Scan the codebase and produce a prioritized list of technical debt items.

## Steps

1. Glob all source files in `src/`, `app/`, `api/`, `components/`
2. For each file, check:
   - TODO / FIXME / HACK / XXX comments
   - Functions longer than 50 lines
   - Deeply nested conditionals (3+ levels)
   - Hardcoded values (magic numbers, inline URLs, credentials)
   - Missing error handling on IO or network calls
   - Duplicated logic (similar blocks in 2+ places)
3. Output a markdown table: `File | Line | Issue | Severity`

## Usage

```
/techdebt
/techdebt src/api/
```

## Output Format

| File | Line | Issue | Severity |
|------|------|-------|----------|
| api/users.py | 42 | TODO: add pagination | Medium |
