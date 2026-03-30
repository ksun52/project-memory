## Workflow Orchestration

### 1. Plan Node Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- Write plan to `tasks/todo.md` with checkable items; check in before starting       
- If something goes sideways, STOP and re-plan immediately - don't keep pushing
- Use plan mode for verification steps, not just building
- Mark items complete as you go; add results section when done

### 2. Subagent Strategy
- Use subagents liberally to keep main contect window clean
- Offload research, exploration, and parallel analysis to subagents

### 3. Self-Improvement Loop
- After any correction: update `tasks/lessons.md` with the pattern and a rule to prevent it
- Review `tasks/lessons.md` at session start

### 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- After implementation, run the Critical Reflection checklist

### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests - then resolve them

## Task Management
1. **Plan First**: Write plan to `tasks/todo.md` with checkable items 
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to `tasks/todo.md`

## Critical Reflection Checklist
  After implementing changes, review for:
  - **Scope drift:** Did you expand, reduce, or alter the original scope?
  - **Unintended functionality:** Did you add anything beyond what was requested?
  - **Intent changes:** Any changes in intent not previously agreed upon?
  - **Major assumptions:** Any significant assumptions made without confirmation?
  - **Missed tasks:** Did you fail to address any required items?

## Core Principles
- **Simplicity First**: Make every change as simple as possible. Inpact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.