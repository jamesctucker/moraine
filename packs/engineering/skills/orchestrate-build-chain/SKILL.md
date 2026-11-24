---
name: orchestrate-build-chain
description: Orchestrate a multi-issue build chain by delegating each issue to a fresh subagent, running a review pass between issues, and merging stacked PRs bottom-up. Use when the user says "run the build chain", "resume the pods chain", "delegate the milestones", or has a spec broken into a chain of dependent issues to build end-to-end. Not for a single issue — use implement-milestone directly.
---

# orchestrate-build-chain

One orchestrator session drives a chain of dependent issues (e.g. PROJ-101–110) from a spec that has already been broken into issues. The orchestrator stays small: each issue is built by a fresh `general` subagent following `implement-milestone`, a review pass runs between issues, and stacked PRs merge bottom-up.

## When to use

- A spec has been broken into a dependency chain (tracker `Blocked by` wiring + milestone order).
- The user wants the chain built in one sustained run rather than manually issue-by-issue.
- Not for a single issue or a research/triage task.

## Roles

| Role | Who | Does |
|------|-----|------|
| **Orchestrator** | this session | holds the plan, delegates, reviews, merges, transitions Linear, keeps context small |
| **Build subagent** | fresh `general` agent per issue | runs `implement-milestone` (spec → branch → tests → test gate → PR) |
| **Review** | `code-review` skill, launched by orchestrator | tiered findings pass between build and merge |

**Child subagents cannot spawn subagents** (no task tool). Every review pass and fix batch must be launched by the orchestrator.

## Setup

1. Read the artifact + Linear chain (`get_issue` with `includeRelations: true`) to confirm order and blockers.
2. Read each issue's `Route:` tag (set by `to-issue`; missing ⇒ treat as creative, ask the user before delegating). Surface the split up front: which issues delegate, which park for the user. **Rotation:** if every issue is rote, say so and suggest the user hand-build one — their call, not a gate.
3. Persist a **restart anchor** to `memory/staging/<YYYY-MM-DD>.md`: progress, next issue, human gates, mechanics learnings. This is what survives a context loss.
4. Confirm the human's standing gates up front (e.g. app login, on-device smoke, upload approval).

## Per-issue loop

1. **Route check** — `rote` issues delegate per step 2. `creative` issues never go to a build subagent: park the chain and hand the issue to the user — they write the core (blank page; an advisor agent may critique their draft, never write it). Resume the chain when their PR is up.
2. **Delegate** — spawn one `general` subagent for the issue: spec section, branch name, test command, issue ID, and "follow the `implement-milestone` skill."
3. **Verify work exists** — see *Silent failures* below before trusting the report.
4. **Review** — run the `code-review` skill on the branch/PR (gate first, focused reads, tiered findings).
5. **Fix** — apply small findings as orchestrator review-fix commits. Only spawn a fix subagent for big batches (observed: 3 of 4 reviews needed ≤2 fixes).
6. **Merge (stacked order)** — `merge without --delete-branch` → retarget the next PR to main → merge → delete branches only after the last merge. See REFERENCE.md.
7. **Transition Linear** — Backlog → Todo → In Progress (allowed). **Done only on explicit human approval** (autonomy gates in `AGENTS.md`). Comment the PR link.
8. **Loop** to the next issue.

## Silent failures

A subagent can return an empty report after transitioning the Linear issue with **zero repo artifacts** (observed twice). Never assume work exists from the report alone — check all three:

```bash
git -C <repo> branch -a
gh pr list -R <owner>/<repo>
# + the Linear issue state
```

If clean, relaunch a fresh subagent. State was undamaged both times.

## Human gates

Never cross without explicit approval: TestFlight/App Store uploads, production deploys, `Done` transitions, destructive cleanup. Park the chain and surface the blocker.

## Keep context small

The whole point is fresh subagent windows. Don't read full diffs in the orchestrator; let the review findings + test gate be the signal.

## Reference

- `REFERENCE.md` — stacked-PR mechanics, restart-anchor template, observed learnings
- `implement-milestone` skill — per-issue build loop
- `code-review` skill — review pass
- Source: `memory/staging/2026-09-03.md`, `memory/staging/2026-09-10.md`
