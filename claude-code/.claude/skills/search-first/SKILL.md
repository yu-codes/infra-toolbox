---
name: search-first
description: Research-before-coding workflow. Use when the task involves unfamiliar APIs, libraries, or architectural decisions. Read before you write.
---

# Search-First Workflow

Research and understand before writing code. Prevents wasted effort from wrong assumptions.

## When to Use

- Unfamiliar library or API
- Architectural decision with multiple options
- Integration with external service
- Performance-sensitive code
- Security-critical code

## Workflow

### Step 1: Understand the Problem

Before touching any code:
1. Read the relevant source files (imports, existing patterns)
2. Search for similar implementations in the codebase
3. Check documentation for the libraries involved

```bash
# Find existing patterns
grep -rn "pattern_you_need" --include="*.py" --include="*.ts" .
# Check what's already imported
grep -rn "from.*import\|require(" --include="*.py" --include="*.ts" <target-file>
```

### Step 2: Research Options

For external libraries/APIs:
1. Check installed version: `pip show <package>` or `npm ls <package>`
2. Read the docs for that EXACT version
3. Look for usage examples in the codebase
4. Identify breaking changes between versions

### Step 3: Verify Assumptions

Before implementing:
- [ ] I know which library version is installed
- [ ] I've read the API docs for that version
- [ ] I've found similar patterns in this codebase
- [ ] I understand the error handling expectations
- [ ] I know where tests should go

### Step 4: Plan Then Implement

1. Write a brief plan (2-3 sentences) of what you'll do
2. Implement the solution
3. Test it works

## Anti-Patterns

❌ **Don't**: Jump straight to writing code for unfamiliar APIs
❌ **Don't**: Assume library API based on name alone
❌ **Don't**: Copy patterns from a different framework version
❌ **Don't**: Skip reading existing code in the same module

✅ **Do**: Read the existing code first
✅ **Do**: Check installed versions before using APIs
✅ **Do**: Follow patterns already established in the project
✅ **Do**: Verify your solution compiles/runs before moving on
