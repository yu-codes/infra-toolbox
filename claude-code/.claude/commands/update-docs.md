---
description: Update documentation to match current code state.
---

# Update Docs

Synchronize documentation with the current codebase.

## Process

### 1. Identify Stale Docs

```bash
# Find recently changed source files
git log --since="1 week" --name-only --pretty=format: -- '*.py' '*.ts' '*.vue' | sort -u

# Find docs that may be outdated
find . -name "*.md" -newer .git/COMMIT_EDITMSG
```

### 2. Check for Drift

For each changed source file:
- Does the README reference this file's API?
- Are docstrings still accurate?
- Do usage examples still work?
- Are environment variables documented?

### 3. Update

- **API docs**: Match endpoint signatures, request/response schemas
- **README**: Update setup instructions if dependencies changed
- **Docstrings**: Match function signatures and behavior
- **docker-compose**: Document new services/env vars
- **CHANGELOG**: Add entry for notable changes

### 4. Verify

```bash
# Check for broken links
grep -rn "\[.*\](.*\.md)" --include="*.md" . | while read line; do
  file=$(echo "$line" | grep -oP '\(.*?\.md\)' | tr -d '()')
  [ ! -f "$file" ] && echo "BROKEN: $line"
done
```

## Rules

- Keep docs concise — no novels
- Code examples must be copy-pasteable
- Document the "why", not just the "what"
- Remove docs for deleted features
