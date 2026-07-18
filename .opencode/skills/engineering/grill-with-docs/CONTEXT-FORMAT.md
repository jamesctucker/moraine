# CONTEXT.md Format

## Structure

```md
# {Context Name}

{One or two sentence description of what this context is and why it exists.}

## Language

**Order**:
{A one or two sentence description of the term}
_Avoid_: Purchase, transaction

**Invoice**:
A request for payment sent to a customer after delivery.
_Avoid_: Bill, payment request

**Customer**:
A person or organization that places orders.
_Avoid_: Client, buyer, account
```

## Rules

- **Be opinionated.** When multiple words exist for the same concept, pick the best one and list the others as aliases to avoid.
- **Flag conflicts explicitly.** If a term is used ambiguously, call it out in "Flagged ambiguities" with a clear resolution.
- **Keep definitions tight.** One or two sentences max. Define what it IS, not what it does.
- **Show relationships.** Use bold term names and express cardinality where obvious.
- **Only include terms specific to this project's context.** General programming concepts (timeouts, error types, utility patterns) don't belong even if the project uses them extensively. Before adding a term, ask: is this a concept unique to this context, or a general programming concept? Only the former belongs.
- **Group terms under subheadings** when natural clusters emerge. If all terms belong to a single cohesive area, a flat list is fine.
- **Write an example dialogue.** A conversation between a dev and a domain expert that demonstrates how the terms interact naturally and clarifies boundaries between related concepts.

## Where CONTEXT.md lives

**In OpenBench workspace:** Project glossaries live inside `work/<project>/` directories:

```
work/
└── my-project/
    └── CONTEXT.md          ← domain glossary for the project
```

If a project has multiple bounded contexts, use a `CONTEXT-MAP.md` at the project root:

```
work/
└── my-project/
    ├── CONTEXT-MAP.md
    ├── src/
    │   ├── ordering/
    │   │   └── CONTEXT.md
    │   └── billing/
    │       └── CONTEXT.md
```

The skill infers which structure applies by checking for `CONTEXT-MAP.md` first.

## Workspace-level terminology

For concepts that span projects or apply to OpenBench itself (e.g., "skill", "persona", "artifact"), do not create a root-level `CONTEXT.md`. Instead:
- Define them in the relevant `artifacts/` doc
- Or capture them in `memory/index.md` if they are conventions or decisions
- Or store them in the Obsidian vault under the appropriate PARA category
