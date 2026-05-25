# Git Workflow

## Commit Message Format

```
<type>: <description>

<optional body>
```

Types: feat, fix, refactor, docs, test, chore, perf, ci

Examples:
- `feat: add user authentication endpoint`
- `fix: resolve race condition in order processing`
- `refactor: extract payment logic into service layer`

## Branch Strategy

- `main` — production-ready code
- `develop` — integration branch (optional)
- `feat/<name>` — new features
- `fix/<name>` — bug fixes
- `refactor/<name>` — code improvements

## Pull Request Workflow

1. Analyze full commit history (not just latest commit)
2. Use `git diff main...HEAD` to see all changes
3. Draft comprehensive PR summary
4. Include test plan
5. Push with `-u` flag if new branch

## Rules

- Never force push to shared branches
- Rebase feature branches before merge
- Delete branches after merge
- Keep commits atomic — one logical change per commit
