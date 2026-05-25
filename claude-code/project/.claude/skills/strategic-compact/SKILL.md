---
name: strategic-compact
description: Context management — suggests when to compact for optimal session quality. Use during long sessions.
---

# Strategic Compaction

Guide for when to use `/compact` during long sessions to maintain quality.

## When to Compact

| Situation | Action |
|-----------|--------|
| Research done, about to implement | `/compact` — keep only the plan |
| Milestone completed, starting next | `/compact` — shed old context |
| Debugging finished, moving on | `/compact` — remove debug traces |
| Failed approach, trying new one | `/compact` — shed the dead end |
| Context at 60%+ usage | Consider compacting soon |

## When NOT to Compact

| Situation | Why |
|-----------|-----|
| Mid-implementation | You'll lose variable names, file paths, partial state |
| During debugging | You need the error context |
| While tests are failing | Keep the failure context |
| Right after reading many files | That context is still needed |

## Cost-Saving Strategy

| Command | Use When |
|---------|----------|
| `/clear` | Between completely unrelated tasks (free, instant reset) |
| `/compact` | At logical breakpoints within related work |
| `/cost` | Check spending periodically |
| `/model sonnet` | Default — handles 80% of tasks |
| `/model opus` | Complex architecture, deep debugging only |

## Session Structure (Optimal)

```
1. Research phase       → read files, understand codebase
2. /compact             → keep only findings
3. Planning phase       → create implementation plan
4. /compact             → keep only plan
5. Implementation phase → write code
6. /compact             → keep only current progress
7. Verification phase   → run tests, fix issues
8. Done                 → /clear for next task
```

## Signs You Need to Compact

- Claude starts repeating information
- Responses get slower
- Claude forgets earlier decisions
- Context window warning appears
- Token cost per response is climbing
