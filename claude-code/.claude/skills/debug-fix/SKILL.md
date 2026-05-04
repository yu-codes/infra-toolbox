# Skill: debug-fix

Systematically locate and fix a bug with minimal scope changes.

## Steps

1. Read the error message and stack trace in full
2. Identify the exact file and line where the error originates
3. Read that file — understand the surrounding context
4. Form a hypothesis: what is the root cause?
5. Check the hypothesis:
   - Trace inputs backward (what called this?)
   - Check types, null values, off-by-one, async issues
6. Apply the minimal fix
7. Verify the fix does not break adjacent behavior

## Rules

- Fix the root cause, not the symptom
- Do NOT add try/except or error suppression as a fix
- Do NOT refactor while fixing — one change at a time
- After fixing, check if the same pattern exists elsewhere

## Common Patterns

| Symptom | Likely Cause |
|---------|--------------|
| `KeyError` / `undefined` | Missing null check or wrong key name |
| 422 from FastAPI | Pydantic validation mismatch |
| Vue reactivity not updating | Mutating nested object directly |
| CORS error | Backend missing CORS middleware or wrong origin |
| 401 on valid token | Token not sent in `Authorization` header |
