---
name: impeccable
description: Frontend design and UI improvement — design, redesign, critique, audit, polish, or improve any frontend interface (websites, dashboards, app UI, components, forms, settings). Use when the user wants design work on a frontend. Not for backend-only tasks.
version: 3.1.1
user-invocable: true
argument-hint: "[craft|shape · audit|critique · animate|bolder|colorize|delight|layout|overdrive|quieter|typeset · adapt|clarify|distill · harden|onboard|optimize|polish · teach|document|extract|live] [target]"
license: Apache 2.0. Based on Anthropic's frontend-design skill. See NOTICE.md for attribution.
allowed-tools:
  - Bash(npx impeccable *)
---

Designs and iterates production-grade frontend interfaces. Real working code, committed design choices, exceptional craft.

## Setup

Load [reference/setup.md](reference/setup.md) — covers context gathering (PRODUCT.md / DESIGN.md), register identification (brand vs. product), and the loader script.

For general design invocations where no sub-command matches the table below, also load [reference/shared-design-laws.md](reference/shared-design-laws.md). Sub-commands that match the table load their own reference file and skip shared-design-laws.

## Commands

| Command | Category | Description | Reference |
|---|---|---|---|
| `craft [feature]` | Build | Shape, then build a feature end-to-end | [reference/craft.md](reference/craft.md) |
| `shape [feature]` | Build | Plan UX/UI before writing code | [reference/shape.md](reference/shape.md) |
| `teach` | Build | Set up PRODUCT.md and DESIGN.md context | [reference/teach.md](reference/teach.md) |
| `document` | Build | Generate DESIGN.md from existing project code | [reference/document.md](reference/document.md) |
| `extract [target]` | Build | Pull reusable tokens and components into design system | [reference/extract.md](reference/extract.md) |
| `critique [target]` | Evaluate | UX design review with heuristic scoring | [reference/critique.md](reference/critique.md) |
| `audit [target]` | Evaluate | Technical quality checks (a11y, perf, responsive) | [reference/audit.md](reference/audit.md) |
| `polish [target]` | Refine | Final quality pass before shipping | [reference/polish.md](reference/polish.md) |
| `bolder [target]` | Refine | Amplify safe or bland designs | [reference/bolder.md](reference/bolder.md) |
| `quieter [target]` | Refine | Tone down aggressive or overstimulating designs | [reference/quieter.md](reference/quieter.md) |
| `distill [target]` | Refine | Strip to essence, remove complexity | [reference/distill.md](reference/distill.md) |
| `harden [target]` | Refine | Production-ready: errors, i18n, edge cases | [reference/harden.md](reference/harden.md) |
| `onboard [target]` | Refine | Design first-run flows, empty states, activation | [reference/onboard.md](reference/onboard.md) |
| `animate [target]` | Enhance | Add purposeful animations and motion | [reference/animate.md](reference/animate.md) |
| `colorize [target]` | Enhance | Add strategic color to monochromatic UIs | [reference/colorize.md](reference/colorize.md) |
| `typeset [target]` | Enhance | Improve typography hierarchy and fonts | [reference/typeset.md](reference/typeset.md) |
| `layout [target]` | Enhance | Fix spacing, rhythm, and visual hierarchy | [reference/layout.md](reference/layout.md) |
| `delight [target]` | Enhance | Add personality and memorable touches | [reference/delight.md](reference/delight.md) |
| `overdrive [target]` | Enhance | Push past conventional limits | [reference/overdrive.md](reference/overdrive.md) |
| `clarify [target]` | Fix | Improve UX copy, labels, and error messages | [reference/clarify.md](reference/clarify.md) |
| `adapt [target]` | Fix | Adapt for different devices and screen sizes | [reference/adapt.md](reference/adapt.md) |
| `optimize [target]` | Fix | Diagnose and fix UI performance | [reference/optimize.md](reference/optimize.md) |
| `live` | Iterate | Visual variant mode: pick elements in the browser, generate alternatives | [reference/live.md](reference/live.md) |

Plus two management commands: `pin <command>` and `unpin <command>`, detailed below.

### Routing rules

1. **No argument**: render the table above as the user-facing command menu, grouped by category. Ask what they'd like to do.
2. **First word matches a command**: load its reference file and follow its instructions. Everything after the command name is the target.
3. **First word doesn't match**: general design invocation. Load [reference/setup.md](reference/setup.md) and [reference/shared-design-laws.md](reference/shared-design-laws.md), then apply those steps and laws along with the loaded register reference, using the full argument as context.

Setup (context gathering, register) is already loaded by then; sub-commands don't re-invoke `/impeccable`.

If the first word is `craft`, setup still runs first, but [reference/craft.md](reference/craft.md) owns the rest of the flow. If setup invokes `teach` as a blocker, finish teach, refresh context, then resume the original command and target.

## Pin / Unpin

**Pin** creates a standalone shortcut so `/<command>` invokes `/impeccable <command>` directly. **Unpin** removes it. The script writes to every harness directory present in the project.

```bash
node .opencode/skills/design/impeccable/scripts/pin.mjs <pin|unpin> <command>
```

Valid `<command>` is any command from the table above. Report the script's result concisely. Confirm the new shortcut on success, relay stderr verbatim on error.
## Workspace Integration

> Forked from [pbakaus/impeccable](https://github.com/pbakaus/impeccable) for The Garage workspace. Apache 2.0.

### Where output goes

- **Standalone HTML artifacts** (demos, prototypes) → `artifacts/` with sequential numbering
- **Project UI components** → inside the relevant project directory
- **PRODUCT.md / DESIGN.md** → project root (as Impeccable expects)
- **Critique snapshots** → `.impeccable/critique/` (managed by Impeccable scripts)
- **Design explorations** (mood boards, palettes) → `wiki/` under Resources, or `artifacts/`

### Complementary skills

- **`web-design-guidelines`** (in `ux/`) — audits against Vercel's Web Interface Guidelines. Use for guideline compliance checks; Impeccable's `audit` and `critique` evaluate design quality and anti-patterns, not guideline conformance. Both are useful; they test different things.
- **`grill-with-docs`** (in `engineering/`) — when a design choice affects architecture (component boundaries, state management, API contracts), switch to grilling to resolve the structural problem.
- **`diagnose`** (in `engineering/`) — for actual bug diagnosis. Don't use `harden` to debug runtime errors; use `diagnose` for that, then `harden` to prevent future edge cases.

### Context awareness

- Check `memory/index.md` at session start for active project context and recent design decisions.
- If the project has brand/design notes in `wiki/`, respect them — even bold interpretations should stay on-brand.
- Record load-bearing design decisions in `memory/index.md` or as an artifact, not just in code comments.
