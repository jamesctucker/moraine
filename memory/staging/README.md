# Staging — Short-Term Memory

Transient working memory that persists across sessions but isn't yet formalized into long-term memory. Think of this as the agent's and user's shared scratchpad.

## Purpose

- Hold half-formed ideas, quick thoughts, and in-progress context that needs to survive sessions
- Capture decisions or insights that haven't been promoted to a project note yet
- Store restart anchors — what was in progress when the last session ended

## Structure

Files are organized by date: `YYYY-MM-DD.md`. No topic-based structure — that comes after the fact when items are promoted to `wiki/` or `memory/index.md`.

## When to use

- You had an idea during a session but it's not a project yet
- You started working on something but didn't finish
- You made a decision that needs to be remembered but not formalized
- You want to remember something for the next session

## When NOT to use

- Formal session summaries → `memory/sessions/`
- Project-level decisions or research → the project's wiki top note in `wiki/1 Projects/`
- Repo-specific context → the repo's own `AGENTS.md`, registered in `repos/README.md`
- Fully formed projects → scaffold via `scaffold-project` skill into `wiki/1 Projects/`

## Lifecycle

Staging items should either:
1. **Promote** — become a project, area, or entry in `memory/index.md`
2. **Archive** — move to `wiki/4 Archives/` if reference material
3. **Delete** — if no longer relevant (old staging notes are safe to delete)
