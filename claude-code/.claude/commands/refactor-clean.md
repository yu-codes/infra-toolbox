# /refactor-clean

Remove dead code, unused imports, and debug artifacts from the target file or directory.

## Steps

1. Read the target file(s)
2. Remove all `console.log`, `print()` debug statements
3. Remove unused imports (Python: check with `autoflake`-style logic; JS/TS: check usage)
4. Remove unreachable code blocks and commented-out code older than the current feature
5. Ensure no behavior changes — only cleanup

## Usage

```
/refactor-clean <file or directory>
```

## Rules

- Do NOT rename variables or refactor logic
- Do NOT change function signatures
- Only remove — never add
- If unsure about a block, leave it and add a `# TODO: verify unused` comment
