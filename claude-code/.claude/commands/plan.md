---
description: Restate requirements, assess risks, and create step-by-step implementation plan. WAIT for user CONFIRM before touching any code.
argument-hint: <feature or task description>
---

# Plan Command

This command creates a comprehensive implementation plan before writing any code.

## What This Command Does

1. **Restate Requirements** — Clarify what needs to be built
2. **Identify Risks** — Surface potential issues and blockers
3. **Create Step Plan** — Break down into phases
4. **Wait for Confirmation** — MUST receive user approval before proceeding

## How It Works

1. Analyze the request and restate requirements
2. Break down into phases (Backend → Frontend → Docker → Tests)
3. Identify dependencies between components
4. Assess risks and potential blockers
5. Estimate complexity (S/M/L per step)
6. Present the plan and WAIT for explicit confirmation

## Output Format

```
# Implementation Plan: [Feature Name]

## Requirements Restatement
- ...

## Phases
### Phase 1: Backend (FastAPI)
- Step 1: ... (Complexity: S, Risk: Low)
- Step 2: ...

### Phase 2: Frontend (Vue)
- ...

### Phase 3: Docker/Infra
- ...

## Dependencies
- Phase 2 requires Phase 1 API endpoints

## Risks
- HIGH: ...
- MEDIUM: ...

## Estimated Complexity: [S/M/L/XL]

**WAITING FOR CONFIRMATION**: Proceed? (yes/no/modify)
```

## CRITICAL

This command will **NOT** write any code until you explicitly confirm.

## Integration

After planning:
- Use `tdd-workflow` skill to implement test-first
- Use `/build-fix` if build errors occur
- Use `/code-review` to review completed work
