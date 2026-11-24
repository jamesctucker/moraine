# Engineering pack

Spec-driven engineering: review, diagnosis, TDD, planning, build chains, and issue workflows.

## Skills

`code-review`, `diagnose`, `executing-plans`, `implement-milestone`, `improve-codebase-architecture`, `orchestrate-build-chain`, `plan-hardening`, `prototype`, `tdd`, `to-issue`, `wayfinder`, `wizard`, `writing-plans`.

`implement-milestone` runs the deterministic structure check in step 4b when the `quality` pack is also enabled.

## Scripts

- `scripts/verify-deploy-vars.py` — checks that deploy-variable verification is containment-safe before it runs against external services.

## Issue tracking

<!-- [CUSTOMIZE] Configure your issue tracker below. Common options:
     - Linear (personal projects) — https://linear.app
     - Jira / Atlassian Cloud (work projects)
     - GitHub Issues (lightweight)
     Delete or replace this section to match your setup. -->

**Nothing is configured by default.** Add a tracker MCP server to `.opencode/opencode.json` — Linear, Jira, GitHub Issues, or anything else with an MCP server — then enable it there. The `to-issue` skill's workflow (read source → propose breakdown table → wait for human approval → create projects/issues with cross-links) works with whichever tracker the agent has available.

**Layer model — each tool owns one question, cross-link by URL, never duplicate:**

| Question | Where | Granularity |
|----------|-------|-------------|
| Why does this matter? | `wiki/1 Projects/` top notes | Strategic / project |
| What's on the list? | Your tracker — initiatives → projects → issues | Issue / ticket |
| What did the agent decide? | `memory/sessions/` | Session |
| How does this work? | `artifacts/` | Document |

**When to create an issue:** a concrete piece of work with a definition of done — feature, bug, refactor, or task. Not for research, strategy, or session notes.

**Agent workflow with issues:**

```
"Work on ENG-5"
  → agent reads issue (description, comments, git branch name)
  → agent reads repo AGENTS.md + relevant code
  → agent implements on a branch, runs tests, commits
  → agent transitions issue: Backlog → In Progress
  → agent adds comment summarizing what was done + PR link
  → agent pauses — human reviews
  → on approval: human merges, agent transitions In Progress → Done
  → if changes needed: agent updates branch, re-comments
```

**Autonomy gates:**

- **Agent may** (no confirmation needed): read issues, transition Backlog → Todo → In Progress, add comments, attach PR links, create new issues from discovered work.
- **Agent may not** (requires explicit human ask): transition to Done, deploy to staging/prod, delete issues, change priorities or labels without asking.
- **Agent should**: before starting work on an issue, check for blocking issues and existing comments — don't start if context is missing or someone flagged a blocker.

**Backlog triage mode:** when asked "what's next?", list backlog issues, rank by priority → initiative alignment → project fit, and pitch 1-2 options with a one-line rationale. Wait for human confirmation before starting implementation.
