---
name: to-issue
description: Convert an artifact, spec, repo, or current conversation into tracked work — tracer-bullet slices, each declaring what blocks it, published to the configured tracker. Reads the source, proposes a breakdown table (title, what it delivers, label, project, priority, route, blockers), and waits for human confirmation before creating anything. Use when the user says "turn this into issues", "create tickets from...", "break this spec into tickets", "track this as work", or names a tracker to file into.
---

# To Issue

Convert a source document, repo, or conversation into tracker structure (project/milestone → issues). **Never create issues without explicit confirmation** — propose first, create on approval.

## When to use

- "turn this artifact into tickets", "create issues from this repo", "track this work"
- A spec/artifact is complete and ready to be tracked as work
- A repo has TODO/FIXME comments or a roadmap that should become issues
- A design discussion has settled and the work only needs slicing

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
- **From the conversation**: the settled plan is the source — say so in the proposal so the user knows what you're working from.

Map the natural grouping:

- Milestones / phases → projects (or milestones within an existing project)
- Slices within a phase → issues
- Feature / bug / refactor / task → labels

**Prefer vertical slices over horizontal layers.** Agents default to horizontal decomposition (migrations → service → API → frontend), which defers anything touchable to the last issue and makes mid-chain review meaningless. Where the source allows it, cut issues as **end-to-end slices** (tracer bullets): each issue should produce something a human can run and verify in minutes, even if thin. A horizontal split is sometimes genuinely right (shared schema must land first) — when you propose one, say why in the breakdown table's notes.

### Phase 2 — Pull tracker context

Before proposing, check current tracker state so you don't duplicate:

- List projects (and initiatives/epics, if the tracker has them) — where does this fit?
- For a repo: search existing issues in that project to find what's already filed.

Use the source's own vocabulary for issue titles — don't invent terminology. The issue should read like it came from the source, because it did.

### Phase 3 — Draft tracer-bullet slices

Break the work into slices, not layers:

- Each slice cuts a **narrow but complete path through every layer** (schema, API, UI, tests) — vertical, not a horizontal slice of one layer.
- A completed slice is **demoable or verifiable on its own**.
- Each slice is sized to fit **one fresh context window** — roughly what a single `implement-milestone` run can finish.
- Do any **prefactoring first**: "make the change easy, then make the easy change."
- Give each slice its **blocking edges** — the other slices that must complete before it can start. A slice with no blockers can start immediately.

**Wide refactors are the exception.** A wide refactor is one mechanical change (rename a column, retype a shared symbol) whose blast radius fans across the whole codebase, so no vertical slice can land green. Sequence it as **expand–contract**: expand (add the new form beside the old), migrate call sites in batches sized by blast radius (per package, per directory), each batch blocked by the expand, then contract (delete the old form) blocked by every batch. If batches can't stay green alone, let them share an integration branch that all block a final integrate-and-verify slice.

### Phase 4 — Propose breakdown (STOP, ask)

Output a table and ask for confirmation. Do NOT create anything yet.

```markdown
| # | Issue title | Delivers | Label | Project / Milestone | Priority | Route | Blocked by |
|---|-------------|----------|-------|---------------------|----------|-------|------------|
| 1 | Checkout: schema + API for split orders | Customer can submit an order that splits across warehouses, verified by test | Feature | Checkout Redesign | High | creative | — |
| 2 | Checkout: split-order summary UI | Split orders render correctly in the checkout review step | Feature | Checkout Redesign | High | rote | 1 |
```

- **Delivers** — the end-to-end behaviour this slice makes work, from the user's perspective. If you can't state it without naming layers, the slice is horizontal — re-slice.
- **Blocked by** — row numbers (or existing issue IDs/URLs). Use `—` for "can start immediately".
- Below the table: the project/milestone (new or existing) and which parent (initiative, epic, or repo) it belongs to.
- Below that: the source, once, unless rows come from different sections — then add a `Source` column.

Then ask the three questions that actually need a human:

1. Is the granularity right — too coarse, or too fine?
2. Are the blocking edges correct — does each row depend only on what genuinely gates it?
3. Should any rows be merged or split?

Iterate until the user approves.

#### Route: rote or creative (required per issue)

Tag every issue `rote` or `creative` — `orchestrate-build-chain` routes on this tag.

- **rote** — the design is already decided; the work is mechanical execution of it (wiring, CRUD, specified tests, config). Safe to delegate wholesale.
- **creative** — the issue's core is an unsolved design or judgment problem the user should learn from solving. These never go to a build subagent: the user writes the core, an agent critiques.

When in doubt, tag creative. A mis-tagged rote issue costs a parked chain; a mis-tagged creative issue costs the learning — the worse outcome.

### Phase 5 — Create on approval

Only after explicit "yes" / "go ahead":

1. Create or reuse the container first (project, milestone, epic, or repo — whatever the tracker calls it).
2. Create issues **in dependency order — blockers first** — so each "Blocked by" can reference a real identifier. Use the tracker's native blocking relationship where it has one; otherwise put the blocker references in the body.
3. Each issue gets `title`, container, `labels`, `priority`, and a body with `Route: rote|creative` on the first line, what it delivers, acceptance criteria, and a link back to the source path.
4. Map priority onto the tracker's own scale — don't assume a 0–4 numeric range exists.
5. Cross-link: add the new project URL to the source's wiki top note.

If the tracker has required fields the table doesn't cover (assignee, component, issue type), fill them with a stated default and call the default out in the confirmation message.

### Phase 6 — Record

Add a session summary referencing the created issue IDs (e.g. `PROJ-65`). Note in the source artifact that it has been filed.

## Autonomy gates (from AGENTS.md)

- **May**: read issues, create new issues from discovered work, add comments, attach PR links.
- **May not** (needs explicit human ask): close/transition to Done, deploy, delete issues, change priority/label without asking.
- **Should**: before starting work on any issue, check its blockers/dependencies and comments for context.

## Rules

- **Propose before create.** The confirmation gate is the whole point — never batch-create without a yes.
- **Vertical, not horizontal.** If every slice in a batch touches the same layer, you've planned a layer cake, not deliverable work.
- **Naming: use the source's vocabulary.** If the spec says "M3 Comp Fetcher Pipeline", the issue is "M3: Comp Fetcher Pipeline", not "Build comp scraper."
- **No file paths or code snippets in issue bodies** — they go stale. Exception: a prototype snippet that encodes a decision more precisely than prose (state machine, reducer, schema, type shape) — inline the decision-rich part and note it came from a prototype.
- **Cross-link both ways.** Issue → source artifact; source wiki note → project URL.
- **One tracker.** File into the configured tracker only; don't mirror the same issue into two systems.
- **Don't file research/strategy/session notes.** Only concrete work with a definition of done.

## Reference

- `AGENTS.md` → Issue Tracking → layer model and autonomy gates
