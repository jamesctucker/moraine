---
name: grill-with-docs
description: Grilling session that challenges your plan against the existing domain model, sharpens terminology, and updates documentation inline as decisions crystallise. Use when user wants to stress-test a plan against their project's language and documented decisions.
---

# Grill with Docs

Interview the user relentlessly about every aspect of their plan until you reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

Ask the questions one at a time, waiting for feedback on each question before continuing.

If a question can be answered by exploring the codebase, explore the codebase instead.

## When to use

Load this skill when the user:
- Says "grill me", "stress-test this", "poke holes in this plan"
- Wants to validate a design against existing decisions or domain language
- Is proposing something new and wants to be challenged before committing
- Asks to "sharpen" or "tighten" a plan, spec, or architecture doc

## Domain awareness

OpenBench is a workspace, not a single software project. Before grilling, determine which layer the conversation belongs to:

### Workspace level

Discussing infrastructure, skills, agent workflows, or cross-project concerns. Documentation lives here:

```
openbench/
├── artifacts/           ← architecture docs, design plans (numbered: 01-, 02-, etc.)
│   ├── 01-self-improving-loop.md
│   └── 02-ocr-pipeline.md
├── memory/
│   └── index.md         ← active projects, open threads, recent decisions
├── wiki/            ← PARA vault for domain knowledge
└── work/                ← external project repos (when present)
```

### Project level

Discussing a specific software project inside `work/<project>/`. Documentation lives there:

```
work/
└── my-project/
    ├── CONTEXT.md
    ├── docs/
    │   └── adr/
    │       ├── 0001-event-sourced-orders.md
    │       └── 0002-postgres-for-write-model.md
    └── src/
```

If no `work/` project is active, default to workspace level.

### When `work/` projects aren't cloned

The user may discuss a project that isn't physically present in `work/` (e.g., repos tracked in `memory/index.md` but not yet checked out). In this case:
- Check `memory/index.md` for any recorded context about the project
- Ask the user for the relevant domain terms and constraints rather than assuming you can read code
- If a `CONTEXT.md` would be valuable, suggest the user clone the repo first, or offer to draft one in `artifacts/` as a temporary holding doc until the repo is available

### File creation rules

- **Workspace architecture docs** → `artifacts/` using sequential numbering (check existing files for next number)
- **Workspace decisions** → `memory/index.md` under a dated "Recent decisions" section
- **Project glossary** → `work/<project>/CONTEXT.md`
- **Project ADRs** → `work/<project>/docs/adr/` with sequential numbering

Create files lazily — only when you have something to write.

## During the session

### Challenge against existing docs

When the user uses a term or proposes a design, check for conflicts:
- **Artifacts**: Does an existing artifact already address this? (e.g., `01-self-improving-loop.md` covers the skill ecosystem)
- **Memory**: Does `memory/index.md` record a prior decision that contradicts this plan?
- **Obsidian**: Is there a note in the PARA vault with relevant domain knowledge?
- **Project CONTEXT.md**: If in a project context, does the glossary define this term differently?

Call out conflicts immediately: "`memory/index.md` records that we chose X on 2026-05-09, but this plan assumes Y — has something changed?"

### Sharpen fuzzy language

When the user uses vague or overloaded terms, propose a precise canonical term. "You're saying 'account' — do you mean the Customer or the User? Those are different things."

### Discuss concrete scenarios

When domain relationships are being discussed, stress-test them with specific scenarios. Invent scenarios that probe edge cases and force the user to be precise about the boundaries between concepts.

### Cross-reference with code

When the user states how something works, check whether the code agrees. If you find a contradiction, surface it: "Your code cancels entire Orders, but you just said partial cancellation is possible — which is right?"

### Update docs inline

When a term is resolved or a decision crystallises, update documentation right there. Don't batch these up.

**At workspace level:**
- New architecture insight → create or update an `artifacts/` doc
- New decision → append to `memory/index.md` under the current date

**At project level:**
- New term → update `work/<project>/CONTEXT.md` using the format in [CONTEXT-FORMAT.md](./CONTEXT-FORMAT.md)
- Hard-to-reverse, surprising, trade-off decision → offer an ADR using the format in [ADR-FORMAT.md](./ADR-FORMAT.md)

### Offer workspace artifacts generously

At the workspace level, create an artifact when the plan captures:
- A new architectural pattern or workflow
- A cross-project integration strategy
- A design for a new skill, persona, or automation

Use sequential numbering. If the last artifact is `03-workspace-modularity.md`, the next is `04-<slug>.md`.

### Offer ADRs sparingly (project level only)

Only offer to create an ADR when all three are true:

1. **Hard to reverse** — the cost of changing your mind later is meaningful
2. **Surprising without context** — a future reader will wonder "why did they do it this way?"
3. **The result of a real trade-off** — there were genuine alternatives and you picked one for specific reasons

If any of the three is missing, skip the ADR. Record the decision in `memory/index.md` instead.

## Wrapping up

When the grilling session winds down (user signals they're satisfied, or all branches are resolved):

1. **Recap what was decided.** Give a concise numbered list of:
   - Terms that were sharpened or added to `CONTEXT.md`
   - Decisions recorded in `memory/index.md` or as ADRs
   - Artifacts created or updated
   - Open questions that remain unresolved

2. **Flag anything that changed existing docs.** If you updated an artifact or memory entry that existed before this session, call it out explicitly so the user can review.

3. **Suggest session-handoff.** If the session produced meaningful decisions or artifacts, remind the user they can run `session-handoff` to capture the full session context for future agents. Don't invoke it automatically — the user may have more work to do first.
