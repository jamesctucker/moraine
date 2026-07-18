# Spaces

Persistent domain consultants — like Perplexity Spaces — that carry specialized context, expertise, and communication style across sessions. Each space is loaded by name into the agent's context when invoked.

## How They Work

- Each space is a directory under `spaces/` with a standard file structure
- When you say "talk to my Staff Engineer" or `/use-space flip-advisor`, the agent loads the space's context
- Spaces persist decisions, preferences, and domain knowledge in `MEMORY.md`
- OpenCode sessions are tracked automatically via `<!-- space: <name> -->` markers and the sync script
- Think of them as consultants with long-term memory for their domain

## Directory Structure

```
spaces/<name>/
  INSTRUCTIONS.md    # Identity, expertise, style, skills, default context (required)
  MEMORY.md           # Persistent notes across sessions
  SESSIONS.md         # Auto-populated OpenCode session history
  files/              # Reference docs, resources, and related materials
    REFERENCE.md      # Workflows and procedures
    RESOURCES.md      # Sources and external links
```

## Creating a Space

Copy `_template/` into a new directory and fill in `INSTRUCTIONS.md`.

## Building Blocks

| Block | File | Required |
|-------|------|----------|
| Identity + expertise + style + skills | `INSTRUCTIONS.md` | Yes |
| Persistent memory | `MEMORY.md` | No (auto-created from template) |
| OpenCode session history | `SESSIONS.md` | No (auto-populated) |
| Workflows and procedures | `files/REFERENCE.md` | No |
| Sources and external links | `files/RESOURCES.md` | No |

The `skills:` field in `INSTRUCTIONS.md` frontmatter declares which agent skills to load when the space is activated. Example: `skills: [newsletter-edit, perplexity-research]`

## Session History

When a space is loaded (via `/use-space` command or the `space-loader` skill), the agent emits a `<!-- space: <name> -->` marker. The sync script (`scripts/spaces/sync-sessions.ts`) scans OpenCode sessions for these markers and populates each space's `SESSIONS.md` with:

- **Session ID** — the OpenCode chat session ID
- **Host** — the machine hostname (sessions are machine-local)
- **Date** — when the session was created
- **Title** — session title from OpenCode

Sync runs automatically:
- **On space load** — scoped to the loaded space (fast)
- **Every 6 hours** — full reconciliation across all spaces (via cron)

## Active Spaces

<!-- [CUSTOMIZE] List your spaces here. Each row: name, link to INSTRUCTIONS.md, short description. -->

_None yet._ Copy `_template/` into a new directory and fill in `INSTRUCTIONS.md` to create one.
