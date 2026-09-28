# orchestrate-build-chain — Reference

Extended mechanics for running a delegated build chain. Derived from running a 10-issue delegated chain end-to-end.

## Stacked-PR merge order

Dependents are branched off the previous issue's branch, so they stack. Merging in the wrong order breaks the stack.

```
for each issue, bottom-up:
  1. merge the PR WITHOUT --delete-branch
  2. retarget the NEXT (still-open) PR's base to main
  3. merge that PR (again without --delete-branch)
  4. ... repeat ...
  5. after the LAST merge, delete all branches at once
```

- `gh pr merge --delete-branch` on a stacked base **auto-closes dependent PRs**. Reopening and re-basing both fail once the base PR is closed and its branch deleted. Don't do it.
- Merge order is defined by the dependency chain, not by what's ready first.

## Restart anchor template (`memory/staging/<date>.md`)

```md
# <date> — <chain name> RESTART ANCHOR

If a new session sees this and the chain is stalled, resume from here.

## Progress
- <issue> — <state, PR #, commit>

## Next in the chain (NOT started)
- <issue> — <what it is>  ← do not start without human go if gated

## Human gates remaining
- <gate>

## Mechanics learnings
- <merge/subagent/review lessons from this run>
```

Update it as issues land. It is short-term working memory; promote durable mechanics to this skill or the repo `AGENTS.md` when a run ends.

## Orchestrator review cadence that worked

- Run the `code-review` skill per branch: gate first (tests + typecheck must be green before reading), then focused reads, then tiered findings.
- Apply fixes as small orchestrator commits. A fix subagent is only worth it for a big batch.
- Review before merge, every time — self-authored "solid" branches still hid real findings (4 in one concurrency branch).

## Delegation notes

- Give each build subagent a **fresh context window** and the full issue text — don't assume it can see the orchestrator's history.
- Subagents that fail silently still often transition the Linear issue; state and artifacts can diverge. Always reconcile.
- Mobbin/design gates and other spec-time steps can run *inside* the build subagent; capture citations in the PR body.

## Human gates (typical)

- Hosted/admin actions (flip `is_admin`, seed secrets, run hosted migrations)
- On-device smoke against hosted infra
- TestFlight / App Store upload + bundle-id lock
- `Done` transitions and any production deploy
