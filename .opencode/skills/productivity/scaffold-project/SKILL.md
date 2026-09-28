---
name: scaffold-project
description: Scaffold a new project, area, cadence, or resource in The Garage with proper PARA placement, top-note structure, and memory/manifest updates. Interviews first, pushes back on vague scope, writes consistent files. Use when user says "scaffold", "start a new project", "kick off", "set up X", or wants to promote an existing idea to active.
---

# Scaffold Project

Set up a new project, area, cadence, or resource with consistent structure across Obsidian, memory, and the project manifest. Always interview first; never assume.

## When to use

Load this skill when the user:
- Says "scaffold a project", "start a new project", "kick off X", "set up X"
- Wants to capture an ongoing area of responsibility
- Wants to set up a recurring cadence (newsletter, weekly review, etc.)
- Wants to promote an existing idea to active (`--promote-existing`)
- Says "I need a top note for X" or "I need to add a new [project|area|cadence]"

## PARA quick reference

| Type | Has finish line? | Goes in | Has sub-cadences? |
|------|------------------|---------|-------------------|
| **Project** | Yes | `1 Projects/<Name>/` | No |
| **Area** | No (ongoing responsibility) | `2 Areas/<Name>.md` or `2 Areas/<Name>/` | Optional |
| **Cadence** | No (recurring activity) | `2 Areas/<Parent>/<Name>/` | Yes (it is the cadence) |
| **Resource** | No (reference) | `3 Resources/<Name>.md` | No |

**Pattern choice for areas:** single file (`Homelab.md`) when the area is just one note; directory with `00 Top Note.md` when it has sub-cadences, sub-projects, or > 50 lines of content (e.g., `Garden Club/`). Default to single file unless the area needs sub-structure.

**Naming:** directory names use Title Case for proper nouns and multi-word names (matches existing pattern: `Reading Log/`, `Home Renovation/`, `Garden Club/`). Single-file area/resource notes use Title Case + `.md` (e.g., `Homelab.md`).

## Phase 1: INTERVIEW

Ask the questions **one at a time**, waiting for the answer before continuing. For each question, surface your recommended answer and the reasoning behind it.

1. **"What are you trying to capture?"** — short description. Distill verbose answers.

2. **"Does this have a finish line or a deadline?"**
   - Yes → Project. Proceed with project questions.
   - No → "Is it an ongoing responsibility (Area), a recurring activity under an area (Cadence), or a topic you want to reference (Resource)?"
   - "Depends" / "kind of both" → probe further; don't accept it as an answer.

3. **"What does done look like in one sentence?"** (Projects only)
   - Push back on vague: "feel good about it", "be better", "finish the work".
   - Concrete examples: "Ship the modal to production", "Users can filter by date range with no errors".
   - If they can't say it in one sentence, suggest making it smaller or moving to Cadence.

4. **"What does this replace or pause?"**
   - Every active project should justify its slot.
   - If nothing: ask "Why is this worth starting now?" — a project competing with nothing usually isn't real.

5. **"What's the smallest version that proves the hypothesis?"**
   - Guards against scope creep.
   - Push back if the smallest version is still > 1 month of work.

6. **"What existing artifacts / notes / repos should this link to?"**
   - Check `memory/index.md` and `artifacts/` for relevant prior work.
   - Avoid orphan projects.

7. **"What's the first concrete next-action?"**
   - Must be an action: verb + concrete deliverable + time-bound.
   - Push back on vague: "think about X", "research options", "explore".
   - Concrete examples: "Write the API contract doc by Friday", "Pair with Eliza on Tuesday to design the filter panel".

## Phase 2: SCAFFOLD

Write the files using [templates.md](./templates.md). Confirm each file before writing it; never silently create wrong-PARA files or vague frontmatter.

### Project scaffold

1. Create `wiki/1 Projects/<Name>/00 Top Note.md` from project template.
2. If the project needs a written spec (probe in interview: "Is this complex enough to warrant a spec doc?"), create `artifacts/NN-<slug>.md` from spec template. Use the next sequential number; check existing artifacts.
3. Update `wiki/1 Projects/projects.md` — add a row to the right section (Active / Paused / Ideas).
4. Update `memory/index.md`:
   - Add to the matching section under `## Active projects` (or Paused/Ideas)
   - Append a `Recent decisions (YYYY-MM-DD)` entry capturing key choices from the interview
   - Add an open thread under `## Open threads` if the project has unresolved questions or hard deadlines

### Area scaffold

1. Create `wiki/2 Areas/<Name>.md` (single file) OR `wiki/2 Areas/<Name>/00 Top Note.md` (directory), from the area template.
2. If directory pattern, the area's top note should list its cadences and active projects (see template).
3. Update `wiki/2 Areas/areas.md` (the index file) — add a row.
4. Update `memory/index.md` — add to `## Areas` section, log decision.

### Cadence scaffold

1. Confirm parent area exists. If not, scaffold the area first (recursively).
2. Create `wiki/2 Areas/<Parent>/<Name>/00 Top Note.md` from cadence template.
3. Update parent area's top note — link to the new cadence in the `## Cadences` section.
4. Update `memory/index.md` — note under the parent area's entry in `## Areas`.

### Resource scaffold

1. Create `wiki/3 Resources/<Name>.md` from resource template.
2. Minimal or no `memory/index.md` update.

## Push-back rules

**Refuse to scaffold (and explain why):**
- No one-sentence "done" definition (projects)
- `next-action` is vague
- User can't name what this competes with or what it pauses
- Project has no clear top note destination (no parent area when one is implied)

**Push back, then proceed if user clarifies:**
- "Is this a project or a cadence?" — if they can't decide, default to cadence under an existing area
- Scope creep in the smallest-version answer
- Orphan project with no links
- Status value not in the allowed set (`idea | active | paused | backlog` for projects; `active` for areas/cadences/resources)

**Never silently:**
- Skip the interview (even for "simple" cases — the questions matter)
- Create files in the wrong PARA folder
- Use a vague `next-action`
- Override an existing file without confirmation

## Promote existing (`--promote-existing`)

When the user wants to change a project's status (idea → active, active → paused, paused → active):

1. Read the existing top note.
2. Confirm the new status with the user, the reason, and any resume condition (for pauses).
3. Update the top note's frontmatter (`status`, `last-reviewed`, possibly `next-action` and `tags`).
4. Update `wiki/1 Projects/projects.md` — move the row to the new section.
5. Update `memory/index.md`:
   - Move the entry to the matching section
   - Add a decision log entry under `## Recent decisions`
   - Add an open thread if the pause has a resume condition
6. If promoting to active, ask: "Does this pause any other project?" — every active should justify its slot.

Allowed transitions: `idea → active`, `idea → backlog`, `active → paused`, `paused → active`, `active → paused → idea` (give up), `* → archived` (move to `4 Archives/`).

## Wrapping up

When scaffolding is done:

1. **Recap what was created/updated.** Numbered list with file paths.
2. **Flag wikilinks that may need updating.** Search for `[[OldName]]` patterns elsewhere; if any reference the project under its old path, surface them.
3. **Offer session-handoff.** If the scaffolding produced meaningful decisions, remind the user they can run `session-handoff` to capture the full session context for future agents.

## Reference

See [templates.md](./templates.md) for all file templates and frontmatter schemas.
