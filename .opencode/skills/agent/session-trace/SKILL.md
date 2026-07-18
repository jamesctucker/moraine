---
name: session-trace
description: Replay an agent session — extract reasoning, decisions, tool calls, and timeline from a session file into a structured trace. Use when asked to debug a session, audit agent behavior, or understand what happened in a past session.
---

# Session Trace

Reads a session file from `memory/sessions/`, extracts structured events (reasoning steps, decisions, tool calls, artifacts), and writes a trace to `memory/sessions/YYYY-MM-DD.trace.md`.

## When to use

- User asks "why did the agent do X in that session?"
- User asks "what tools were called in session Y?"
- User wants a structured timeline of a past session
- Debugging unexpected outcomes
- Building trust through transparency

## Workflow

### 1. Pick a session file

Session files follow `memory/sessions/YYYY-MM-DD-<topic>.md`. Choose one by name or ask the user which session to trace.

```bash
ls memory/sessions/ | head -20
```

### 2. Read the session file

```bash
cat memory/sessions/<filename>.md
```

### 3. Write the structured trace

Produce a trace file at `memory/sessions/YYYY-MM-DD.trace.md` with the following sections:

```markdown
# Session Trace — YYYY-MM-DD: <topic>

**Source:** <filename>
**Generated:** <timestamp>

## Timeline

| Time (approx) | Event type | Description | Tool used |
|--------------|------------|-------------|-----------|
| T+0m | task | User asked: <original query> | — |
| T+1m | reasoning | Agent analyzed <X> | — |
| T+3m | tool | Searched for <pattern> | search tool |
| T+5m | tool | Read <file> | read |
| T+8m | decision | Decided to <Y> | — |
| T+10m | tool | Edited <file> | edit |
| T+15m | verification | Ran <command> | bash |

## Reasoning steps

1. **Understand request** — <agent's analysis of the task>
2. **Explore codebase** — <files read, patterns searched>
3. **Form hypothesis** — <what the agent expected to find>
4. **Implement** — <changes made>
5. **Verify** — <tests or commands run>

## Decisions

| Decision | Rationale | Context |
|----------|-----------|---------|
| <decision> | <why> | <source section in session file> |

## Tool calls

| Tool | Count | Purpose |
|------|-------|---------|
| read | N | Reading session file, configs |
| search | N | Searching for patterns |
| edit | N | Making changes |
| bash | N | Running commands |

## Artifacts created or modified

- `<file>` — <purpose>

## Notes

- <any caveats, uncertainties, or cross-references>
```

### 4. How to extract events

Parse the session file's sections:

- **## Accomplished** / **## What was done** — Contains tool call references (e.g., "Used grep to find...", "Edited file X", "Ran python script Y")
- **## Decisions** / **## Key Decisions** — Extract decision + rationale pairs
- **## Artifacts** — Files created or modified with descriptions
- **## Verification** — Commands run and their results

For timeline estimation, assume:
- Reading/searching: ~1-3 min per step
- Editing/writing: ~3-5 min per file
- Running commands: ~1 min per command
- Verification: ~2-5 min

These are best-effort estimates. The exact timing is not critical — the structure is what provides value.

### 5. Review with the user

Present the trace and ask:
- Does the timeline look accurate?
- Are there missing steps?
- Would you like me to add anything?

## Example

Given this session file content:
```
## Accomplished
- Searched sessions for "authentication" — 3 matches
- Read auth controller at work/my-project/app/controllers/auth_controller.rb
- Decided to add session timeout
- Edited auth_controller.rb (+12 lines)
- Ran rails test and all passed
```

The trace would produce:
```
| T+0m | task | Search + fix auth | — |
| T+2m | tool | session search "authentication" | session-search |
| T+5m | tool | Read auth_controller.rb | read |
| T+8m | decision | Add session timeout | — |
| T+12m | tool | Edit auth_controller.rb | edit |
| T+15m | verification | rails test | bash |
```
