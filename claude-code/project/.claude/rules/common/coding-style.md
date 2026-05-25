# Coding Style

## Core Principles

### KISS (Keep It Simple)
- Prefer the simplest solution that actually works
- Avoid premature optimization
- Optimize for clarity over cleverness

### DRY (Don't Repeat Yourself)
- Extract repeated logic into shared functions or utilities
- Avoid copy-paste implementation drift
- Introduce abstractions when repetition is real, not speculative

### YAGNI (You Aren't Gonna Need It)
- Do not build features or abstractions before they are needed
- Avoid speculative generality
- Start simple, then refactor when the pressure is real

## File Organization

MANY SMALL FILES > FEW LARGE FILES:
- High cohesion, low coupling
- 200–400 lines typical, 800 max
- Extract utilities from large modules
- Organize by feature/domain, not by type

## Error Handling

- Handle errors explicitly at every level
- Provide user-friendly error messages in UI-facing code
- Log detailed error context on the server side
- Never silently swallow errors

## Input Validation

- Validate all user input before processing
- Use schema-based validation (Pydantic / Zod)
- Fail fast with clear error messages
- Never trust external data (API responses, user input, file content)

## Naming Conventions

- Python: snake_case for variables/functions, PascalCase for classes, UPPER_SNAKE_CASE for constants
- Vue/TS: camelCase for variables/functions, PascalCase for components/interfaces
- Booleans: prefer `is_`, `has_`, `should_`, `can_` prefixes
- Be descriptive — avoid abbreviations unless universally understood

## Code Smells to Avoid

- **Deep Nesting**: Prefer early returns over nested conditionals
- **Magic Numbers**: Use named constants for thresholds, delays, and limits
- **Long Functions**: Split large functions into focused pieces (<50 lines)
- **God Objects**: Break monolithic classes into focused modules

## Code Quality Checklist

Before marking work complete:
- [ ] Code is readable and well-named
- [ ] Functions are small (<50 lines)
- [ ] Files are focused (<800 lines)
- [ ] No deep nesting (>3 levels)
- [ ] Proper error handling
- [ ] No hardcoded values (use constants or config)
