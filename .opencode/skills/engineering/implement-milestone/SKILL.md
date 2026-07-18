---
name: implement-milestone
description: Spec-driven implementation of a single milestone/feature with a mandatory PR-review pass and a green test gate. Use when the user says "implement milestone X", "build M3", "work on THE-5", or points at a Linear issue / artifact section and wants it built end-to-end. Not for research, triage, or pure code review.
---

# implement-milestone

Implement one milestone from a spec (artifact section or Linear issue), ship it on a branch with tests, run the **test gate**, do a **self-review pass**, then hand off for **human PR review** and apply every piece of feedback before the issue is closed.

This skill encodes the loop that should mature across milestone implementations: every milestone ends with "PR feedback applied / all review findings addressed" **and** a full green test suite (e.g. 68/68, 117ms) — never "implemented, will test later."

## Layer model

Follow the layer model in `AGENTS.md` → Issue Tracking. Read the spec section before coding — don't re-derive the design.

## Workflow

### 1. Load context
- Read the milestone's spec section (artifact or Linear issue description) and any linked decisions/comments. If the spec or comment thread is large, compress with `headroom_compress` first.
- Read the repo's `AGENTS.md` for commands, branch naming, and conventions.
- Skim the relevant existing code so the new code matches surrounding style.
- Identify the Linear issue ID and target branch name (repo convention, e.g. `feature/the-5-m3-comp-fetcher-pipeline`).

### 2. Branch
- Create the branch from the repo's default base. Announce the branch name.

### 3. Implement with tests
- Build the feature **and** its tests in the same pass. Match the repo test framework (`bun test`, `bin/rails test`, etc.).
- Favor injectable dependencies (pass `fetchFn`/clock/clients) so network and time are testable.
- Preserve risk signals: when a value is estimated/uncertain, encode it explicitly (e.g. `confidence:"low"`) rather than silently guessing.
- Graceful degradation: on upstream/network failure, fall back and propagate a partial/failed status — never fabricate data (especially dates/timestamps).

### 4. Test gate (MANDATORY — do not skip)
Run the repo's full test command **and** typecheck. Both must be green before you claim done.
- Record the result: test count, typecheck status, and any framework-specific metrics the repo reports.
- If red, fix until green. A red gate blocks the PR.

### 5. Self-review pass
Before opening the PR, re-read your own diff against the recurring bug classes below and fix anything found. If none of the scraper/pipeline items apply, check the generic list. Produce a 3–5 line self-review note in the PR/issue comment.

**Generic items (all milestone types):**
- No dead code, commented-out blocks, or leftover debug logging.
- No hardcoded secrets, tokens, or credentials.
- Public APIs and exported functions have type annotations and brief docs.
- Error paths are tested, not just the happy path.

### 6. Open PR + comment, transition issue
- Push the branch and open a PR (or just push if PRs aren't used).
- Add a Linear comment: what was implemented, key decisions, the test-gate result, and the self-review note. Link the spec section and PR.
- Before transitioning, check `includeRelations: true` for blocking issues — don't start if someone flagged a blocker.
- Transition the issue **Backlog → Todo → In Progress** (allowed without asking).

### 7. Wait for human PR review
- Hand off and wait. Do **not** merge, deploy, or mark Done.
- When review feedback arrives, **apply every finding** (triage as P0/P1/P2 but don't silently drop any), re-run the test gate, and update the PR/comment with "all review findings addressed".

### 8. Closeout (human-gated)
- Only after explicit human approval: the human merges; on merge, transition **In Progress → Done**.
- Write a `memory/sessions/` summary (accomplished, decisions, artifacts, next).

## Recurring review-finding checklist

These categories surfaced in human PR reviews on HTTP-scraper / data-pipeline milestones (see References). Apply when the diff touches external HTTP, caching, or untrusted input. For other milestone types (UI, CLI, data-only), check the repo's own `AGENTS.md` for a project-specific rubric — if none exists, use the generic items below and add repo-specific ones as they emerge.

- **Cache poisoning** — failed upstream responses must not be cached for the full TTL; bypass/retry on `failed` status.
- **No date fabrication** — parse real dates; if absent, leave null. Never invent `2024-01-01` style defaults. Use ISO-8601 everywhere (DB writes + returned objects).
- **Injection sanitization** — sanitize any user/entity input that reaches SPARQL/SQL/HTML/shell (entity IDs, search terms, item numbers).
- **Real identity + rate-limit hygiene** — set a real `User-Agent` and log rate-limit/backoff events on external HTTP.
- **Partial/failed-signal propagation** — return a result object carrying `status`/`error` instead of throwing; let the failed signal flow through the adapter chain.
- **Options-based APIs** — prefer `doThing({ a, b })` over positional args; update all callers.
- **Enum/contract docs** — document confidence enums and shared contracts; keep the single source of truth authoritative.
- **Config-drift** — if you add/remove an env var, update **all** layers (deploy configs, `.env` templates, preflight checks); don't leave a stale name.

## Autonomy gates

Follow `AGENTS.md` → Issue Tracking → Autonomy gates (same model as `linearize`). Additionally: apply **all** PR review feedback; never close an issue with outstanding review findings.

## Reference
- Pattern source: example milestone implementation sessions — the review checklist above derives from findings in real-world sessions
- Test gate + review loop observed in: periodic reviews ("review-then-fix double-check" pattern)
- Linear workflow: `AGENTS.md` → Issue Tracking
