---
name: linearize
description: Convert an artifact, spec, or repo into Linear issues and projects. Reads the source, proposes a breakdown table (issue title, label, project, priority), and waits for human confirmation before creating anything. Use when the user says "linearize this", "turn this into issues", "create Linear issues from...", "break this spec into tickets", "track this as work in Linear".
---

# Linearize

Convert a source document or repo into Linear structure (initiatives → projects → issues). Encodes the "Linearizing existing work" workflow from `AGENTS.md`. **Never create issues without explicit confirmation** — propose first, create on approval.

## When to use

- "linearize this spec", "turn this artifact into tickets", "create Linear issues from this repo"
- A spec/artifact is complete and ready to be tracked as work
- A repo has TODO/FIXME comments or a roadmap that should become issues

## Layer model (don't violate)

| Question | Where | Never duplicate |
|----------|-------|-----------------|
| Why does this matter? | `wiki/1 Projects/` top notes | |
| What's on the list? | Linear (initiatives → projects → issues) | |
| What did the agent decide? | `memory/sessions/` | |
| How does it work? | `artifacts/` | |

Cross-link by URL. The wiki/artifact owns intent; Linear owns the list. Issue descriptions link back to the source; the source's wiki top note gets the Linear project URL.

## Workflow

### Phase 1 — Identify source + scope

Determine what you're linearizing:

- **From an artifact** (e.g. `artifacts/15-payment-gateway-integration.md`): read it fully.
- **From a repo** (e.g. `work/my-project/`): read `AGENTS.md`, `README.md`, `TODO.md`/`ROADMAP.md`; scan for `TODO`/`FIXME`.

Map the natural breakdown:

- Milestones / phases → Linear projects (or milestones within an existing project)
- Sections / tasks within phases → Linear issues
- Feature / bug / refactor / task → `labels` (Bug, Feature, Improvement)

### Phase 2 — Pull Linear context

Before proposing, check current Linear state so you don't duplicate:

- `linear_list_projects` / `linear_list_initiatives` — where does this fit?
- For a repo: `linear_list_issues` filtered by project to find existing issues.

Use the artifact's own section names for issue titles — don't invent terminology. The issue should read like it came from the source, because it did.

### Phase 3 — Propose breakdown (STOP, ask)

Output a table and ask for confirmation. Do NOT create anything yet.

```markdown
| # | Issue title (from source section) | Label | Project / Initiative | Priority | Source ref |
|---|-----------------------------------|-------|----------------------|----------|------------|
| 1 | M4: SSE Evaluation Orchestrator   | Feature | Example Project | High | artifacts/15 § M4 |
```

Also name the Linear project (new or existing) and which initiative it parents to.

### Phase 4 — Create on approval

Only after explicit "yes" / "go ahead":

- `linear_save_project` (if new) — set team `THE`, link initiative.
- `linear_save_issue` per row — set `title`, `team: "THE"`, `project`, `labels`, `priority` (0=None, 1=Urgent, 2=High, 3=Medium, 4=Low), and a `description` linking back to the source path.
- Cross-link: add the new Linear project/initiative URL to the source's wiki top note.

### Phase 5 — Record

Add a session summary referencing the created issue IDs (e.g. `ENG-65`). Note in the source artifact that it has been linearized.

## Autonomy gates (from AGENTS.md)

- **May**: read issues, create new issues from discovered work, add comments, attach PR links.
- **May not** (needs explicit human ask): transition to Done, deploy, delete issues, change priority/label without asking.
- **Should**: before starting work on any issue, check `includeRelations: true` and comments for blockers.

## Rules

- **Propose before create.** The confirmation gate is the whole point — never batch-create without a yes.
- **Naming: use the source's vocabulary.** If the spec says "M3 Comp Fetcher Pipeline", the issue is "M3: Comp Fetcher Pipeline", not "Build comp scraper."
- **Cross-link both ways.** Linear issue → source artifact; source wiki note → Linear project URL.
- **Don't linearize research/strategy/session notes.** Only concrete work with a definition of done.

## Reference

- `AGENTS.md` → Issue Tracking → "Linearizing existing work" (canonical workflow)
- `memory/sessions/2026-07-08-linear-integration.md` — integration setup + layer model
