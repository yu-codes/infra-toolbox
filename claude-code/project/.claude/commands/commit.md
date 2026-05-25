---
description: Analyze staged changes, write a Conventional Commit message, show preview, and commit on confirmation.
argument-hint: "[scope]" optional — e.g. "auth" or "api/users"
---

# Smart Commit

Analyze staged changes and produce a Conventional Commit message.

## Workflow

1. **Check staged changes** — Run `git diff --staged` and `git status`
2. **Identify change type** — Determine the correct commit type from the diff
3. **Write message** — Generate commit message following Conventional Commits spec
4. **Show preview** — Display the full commit message for approval
5. **Commit on confirmation** — Run `git commit -m "..."` only after explicit approval

## Commit Types

| Type | When to use |
|------|-------------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `refactor` | Code change with no behavior change |
| `perf` | Performance improvement |
| `test` | Adding or updating tests |
| `docs` | Documentation only |
| `chore` | Build process, dependency updates, tooling |
| `ci` | CI/CD pipeline changes |
| `style` | Formatting, whitespace (no logic change) |
| `revert` | Reverting a previous commit |

## Message Format

```
<type>(<optional scope>): <description>

<optional body — explain WHY, not what>

<optional footer>
BREAKING CHANGE: <description>
Closes #<issue>
```

## Rules

- Description: imperative mood, lowercase, no period, max 72 chars
- Body: explain motivation, not mechanics — "why" not "what"
- Scope: use the affected module/component (e.g., `auth`, `api`, `frontend`)
- Breaking changes: add `!` after type+scope AND `BREAKING CHANGE:` footer
- Reference issues when relevant: `Closes #42`, `Fixes #123`

## Preview Format

```
Staged files: 4 changed, 2 new
─────────────────────────────
Proposed commit:

  feat(auth): add JWT refresh token rotation

  Implements sliding window refresh tokens to reduce re-auth friction.
  Access tokens expire in 15m, refresh tokens in 7d with rotation.

  Closes #87

─────────────────────────────
Proceed? (yes / edit / cancel)
```

## CRITICAL

- NEVER commit without showing the preview first
- NEVER include unstaged changes
- If nothing is staged, remind the user to `git add` first
- If changes span multiple unrelated concerns, suggest splitting into multiple commits
