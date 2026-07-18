---
name: session-search
description: Search past agent sessions for discussions, decisions, and context. Use when the user asks about past discussions, decisions, or anything that was covered in a previous session.
---

# Session Search

Search past agent session records using a full-text search index built from `memory/sessions/` and `memory/staging/`.

## When to use

User asks something like:
- "what did we discuss about X?"
- "search sessions for..."
- "find past decisions on..."
- "have we talked about..."
- "when did we decide X?"
- "what was the outcome of the session on Y?"

## Workflow

### 1. Index (if needed)

If `memory/.index/sessions.db` doesn't exist or is stale, rebuild:

```bash
python scripts/workspace/session-index.py index
```

This indexes all `*.md` files in `memory/sessions/` and `memory/staging/`. It's fast (<100ms for ~40 files). The index is always rebuilt from scratch.

### 2. Search

```bash
python scripts/workspace/session-index.py search "<query>"
```

**Options:**
- `--limit N` — max results (default: 10)
- `--dates YYYY-MM-DD..YYYY-MM-DD` — date range filter
- `--section decisions` — filter to a specific section (`accomplishments`, `decisions`, `in_progress`, `artifacts`, `notes`)
- `--project NAME` — filter by project name (e.g., `my-api`, `my-frontend`)

**Examples:**
```bash
python scripts/workspace/session-index.py search "authentication"
python scripts/workspace/session-index.py search "Grove deploy" --limit 5
python scripts/workspace/session-index.py search "OpenHuman comparison" --section decisions
python scripts/workspace/session-index.py search "gift sheet" --dates 2026-05-01..2026-05-31 --project my-api
```

### 3. Read matching sessions

If the search results reference a specific session, read the full session file for more context:

```bash
# Read a specific session file
cat memory/sessions/<YYYY-MM-DD>-<topic>.md

# Read a specific staging file
cat memory/staging/<YYYY-MM-DD>.md
```

## How it works

- Builds an SQLite FTS5 index over all session and staging markdown files
- Tokenizer: `porter unicode61` — Porter stemming (e.g., "auth" matches "authentication") + Unicode-aware tokenization
- Each H2 section (`## Accomplished`, `## Decisions`, etc.) is indexed as a separate row with a `section` tag for targeted queries
- Wikilinks (`[[path/to/file.md|title]]`) and `work/<repo>/` paths are extracted as `project_links` for project-scoped search
- Full rebuild on every index run — trivial (~40 files, <100ms)
- Index stored at `memory/.index/sessions.db` (gitignored)
