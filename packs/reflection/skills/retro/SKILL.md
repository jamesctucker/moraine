---
name: retro
description: Run a post-session retrospective on the agent's environment — navigation gaps, missing automated checks, steering no-ops, token waste, and information blind spots from one session, ranked by severity. Use when a session ran long, needed repeated correction, or the user asks for a retro or post-mortem on a single session.
---

# Retro

You are improving the agent's **environment**, not the work product. The target is the next run, not this one.

## 1. Establish scope

- Default to the current session.
- If the user names an earlier session, find it with `python scripts/workspace/session-index.py search "<term>"`, then read the matching file in `memory/sessions/`.
- Read primary evidence, not the summary: commands that failed, files opened repeatedly, corrections the user made, tool calls that burned tokens, instructions that were ignored.

## 2. Find candidates

Check each category, but only report the ones with evidence.

| Category | Use when | Look for |
|---|---|---|
| **Navigation** | Finding a file took several attempts | Missing pointer in `AGENTS.md` or a repo `AGENTS.md`; hidden dependency between files; docs discoverable only by grep |
| **Automated checks** | A mistake could have been caught mechanically | Repo lint/typecheck/test exists but is unwired; no pre-commit hook or CI job; `scripts/workspace/validate.py` not run after structural edits |
| **Steering** | `AGENTS.md`, a skill, or a memory file did not change behavior | Instructions that duplicate each other, contradict a skill, or restate what a tool already enforces (a **no-op**) |
| **Tool economy** | A call was expensive or repeated | Wrong routing (code → Semble, sessions → `session-index.py`, wiki/artifacts → Hister); whole-file reads where a search would do; repeated fetches of the same source |
| **Information access** | The agent guessed because it could not see | Missing logs, no read access to a service, a doc that lives outside the repo |
| **Memory/skill hygiene** | Workspace context drifted | Stale `memory/staging/` entries, skills that never fire, duplicated guidance between `AGENTS.md`, a skill, and a wiki note |

A repo with no guardrail at all (no pre-commit hook and no CI running its lint/typecheck/test) is itself a finding, not a neutral default. Read the repo's own check command before proposing a new one — an existing but unwired check is the finding, not a reason to reinvent it.

## 3. Classify the fix

| Evidence | Fix |
|---|---|
| Fixed syntactic pattern, banned API, import shape, file-location rule | Deterministic check: linter rule, pre-commit hook, CI job, or a `scripts/workspace/` validator |
| Judgement call (cross-file consistency, "matches surrounding style") | One line in `AGENTS.md` or the repo's own steering file — and only if a check cannot cover it |
| Repeated multi-step workflow | A skill, via `create-skill` |
| Missing context that will recur | `memory/index.md`, a project top note, or an artifact |
| Token burn from routing or config | Change the routing rule or config, not the prompt |

Default to building the check over writing the rule. Reserved prose is for judgement.

## 4. Rank and present

Order by severity:

- **HIGH** — caused a failure, repeated across the session, or added significant cost.
- **MEDIUM** — slowed the session without breaking it.
- **LOW** — polish, or a fix that only pays off if the pattern recurs.

Write the full list to a file, then summarize at most four candidates in chat, each with: what happened, what it cost, the proposed change, and the expected payoff. Never implement without approval.

## 5. Write the retro

Create `memory/reviews/YYYY-MM-DD-<slug>.md`:

```markdown
# Retro: <session name>

**Date:** YYYY-MM-DD
**Session:** <memory/sessions file, or "current session">
**Scope:** what the session was trying to do

## Evidence

<The specific moments that justify each finding: command, file, correction.>

## Candidates

| Severity | Finding | Evidence | Proposed fix |
|---|---|---|---|

## Recommended order

<What to build first and why.>

## Not doing

<Candidates considered and rejected, with the reason.>
```

The date must match the session date; `<slug>` is a short kebab-case label. A daily file without a slug is the periodic `review-memory` output — do not overwrite it.

## Rules

- Evidence over vibes. Every finding cites a command, file, or moment from the session.
- One session, not a trend. If the finding is "this keeps happening", hand off to `review-memory` after the single-session pass.
- The review agent imposes standards, not the implementation agent. The implementation agent carries the context pressure; the review path (see `code-review`) is where rules belong.
- Do not implement. Present, then wait.
- For a skill or doc change, follow `create-skill` rather than inventing structure.
