---
name: to-issue
description: Convert an artifact, spec, or repo into tracked work — a project/milestone container plus issues. Reads the source, proposes a breakdown table (title, label, project, priority, route), and waits for human confirmation before creating anything. Use when the user says "turn this into issues", "create tickets from...", "break this spec into tickets", "track this as work", or names a tracker to file into.
---

# To Issue

Convert a source document or repo into tracker structure (project/milestone → issues). **Never create issues without explicit confirmation** — propose first, create on approval.

## When to use

- "turn this artifact into tickets", "create issues from this repo", "track this work"
- A spec/artifact is complete and ready to be tracked as work
- A repo has TODO/FIXME comments or a roadmap that should become issues

## Tracker independence

This skill assumes an issue-tracker MCP server is configured — Linear, Jira, GitHub Issues, or anything else. Check `AGENTS.md` → Issue Tracking for which tracker this workspace uses. The phases below name the *operations*; use whatever tool names that tracker exposes. If no tracker is configured, say so and stop — don't file issues into a scratch file as a placeholder.

## Layer model (don't violate)

| Question | Where | Never duplicate |
|----------|-------|-----------------|
| Why does this matter? | `wiki/1 Projects/` top notes | |
| What's on the list? | The issue tracker (projects → issues) | |
| What did the agent decide? | `memory/sessions/` | |
| How does it work? | `artifacts/` | |

Cross-link by URL. The wiki/artifact owns intent; the tracker owns the list. Issue descriptions link back to the source; the source's wiki top note gets the project URL.

## Workflow

### Phase 1 — Identify source + scope

Determine what you're filing:

- **From an artifact** (e.g. `artifacts/15-checkout-redesign.md`): read it fully.
- **From a repo** (e.g. `work/my-app/`): read `AGENTS.md`, `README.md`, `TODO.md`/`ROADMAP.md`; scan for `TODO`/`FIXME`.

Map the natural breakdown:

- Milestones / phases → projects (or milestones within an existing project)
- Sections / tasks within phases → issues
- Feature / bug / refactor / task → labels

### Phase 2 — Pull tracker context

Before proposing, check current tracker state so you don't duplicate:

- List projects (and initiatives/epics, if the tracker has them) — where does this fit?
- For a repo: search existing issues in that project to find what's already filed.

Use the artifact's own section names for issue titles — don't invent terminology. The issue should read like it came from the source, because it did.

### Phase 3 — Propose breakdown (STOP, ask)

Output a table and ask for confirmation. Do NOT create anything yet.

```markdown
| # | Issue title (from source section) | Label | Project / Milestone | Priority | Route | Source ref |
|---|-----------------------------------|-------|---------------------|----------|-------|------------|
| 1 | M4: SSE Evaluation Orchestrator   | Feature | Checkout Redesign | High | rote | artifacts/15 § M4 |
```

Also name the project/milestone (new or existing), and which parent (initiative, epic, or repo) it belongs to.

#### Route: rote or creative (required per issue)

Tag every issue `rote` or `creative` — `orchestrate-build-chain` routes on this tag.

- **rote** — the design is already decided; the work is mechanical execution of it (wiring, CRUD, specified tests, config). Safe to delegate wholesale.
- **creative** — the issue's core is an unsolved design or judgment problem the user should learn from solving. These never go to a build subagent: the user writes the core, an agent critiques.

When in doubt, tag creative. A mis-tagged rote issue costs a parked chain; a mis-tagged creative issue costs the learning — the worse outcome.

### Phase 4 — Create on approval

Only after explicit "yes" / "go ahead":

1. Create or reuse the container first (project, milestone, epic, or repo — whatever the tracker calls it).
2. Create one issue per row with `title`, container, `labels`, `priority`, and a `description` linking back to the source path. First line of the description: `Route: rote|creative`.
3. Map priority onto the tracker's own scale — don't assume a 0–4 numeric range exists.
4. Cross-link: add the new project URL to the source's wiki top note.

If the tracker has required fields the table doesn't cover (assignee, component, issue type), fill them with a stated default and call the default out in the confirmation message.

### Phase 5 — Record

Add a session summary referencing the created issue IDs (e.g. `PROJ-65`). Note in the source artifact that it has been filed.

## Autonomy gates (from AGENTS.md)

- **May**: read issues, create new issues from discovered work, add comments, attach PR links.
- **May not** (needs explicit human ask): close/transition to Done, deploy, delete issues, change priority/label without asking.
- **Should**: before starting work on any issue, check its blockers/dependencies and comments for context.

## Rules

- **Propose before create.** The confirmation gate is the whole point — never batch-create without a yes.
- **Naming: use the source's vocabulary.** If the spec says "M3 Comp Fetcher Pipeline", the issue is "M3: Comp Fetcher Pipeline", not "Build comp scraper."
- **Cross-link both ways.** Issue → source artifact; source wiki note → project URL.
- **One tracker.** File into the configured tracker only; don't mirror the same issue into two systems.
- **Don't file research/strategy/session notes.** Only concrete work with a definition of done.

## Reference

- `AGENTS.md` → Issue Tracking → layer model and autonomy gates
