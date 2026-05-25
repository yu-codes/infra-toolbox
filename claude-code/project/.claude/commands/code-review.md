---
description: Code review — local uncommitted changes or GitHub PR (pass PR number/URL for PR mode)
argument-hint: [pr-number | pr-url | blank for local review]
---

# Code Review

**Input**: $ARGUMENTS

## Local Review Mode (default)

Comprehensive security and quality review of uncommitted changes.

### Phase 1 — GATHER
```bash
git diff --name-only HEAD
```
If no changed files, stop: "Nothing to review."

### Phase 2 — REVIEW
Read each changed file in full. Check for:

**Security (CRITICAL):**
- Hardcoded credentials, API keys, tokens
- SQL injection
- Missing input validation
- Path traversal
- Missing auth checks

**Code Quality (HIGH):**
- Functions >50 lines
- Files >800 lines
- Nesting depth >4 levels
- Missing error handling
- console.log / print() debug statements
- Missing tests for new code

**Best Practices (MEDIUM):**
- Mutation patterns
- Missing type hints (Python) / type annotations (TS)
- Accessibility issues

### Phase 3 — REPORT
Generate report with severity, file location, issue, and suggested fix.
Block commit if CRITICAL or HIGH issues found.

## PR Review Mode

If `$ARGUMENTS` contains a PR number or URL:

```bash
gh pr view <NUMBER> --json number,title,body,changedFiles
gh pr diff <NUMBER>
```

Review changed files, run validation, post review to GitHub.

## Verdict

| Condition | Decision |
|-----------|----------|
| Zero CRITICAL/HIGH issues | **APPROVE** |
| Only MEDIUM/LOW issues | **APPROVE** with comments |
| Any HIGH issues | **REQUEST CHANGES** |
| Any CRITICAL issues | **BLOCK** |
