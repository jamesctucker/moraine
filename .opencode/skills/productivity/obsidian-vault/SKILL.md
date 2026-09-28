---
name: obsidian-vault
description: Search, create, and manage notes in the Obsidian vault with wikilinks and PARA organization. Use when user wants to find, create, or organize notes in the Obsidian vault.
---

# Obsidian Vault

## Vault location

`wiki/` at the root of this repo.

## Structure (PARA)

- `1 Projects/` — Active, time-bound efforts with deadlines
- `2 Areas/` — Ongoing responsibilities without end dates
- `3 Resources/` — Reference materials, topics of interest
- `4 Archives/` — Inactive or completed items from the above

Notes go into the appropriate PARA folder. Flat structure within each folder unless nesting is useful.

## Naming conventions

- **Title Case** for note filenames
- **Index notes**: aggregate related topics (e.g., `RAG Index.md`, `Skills Index.md`) placed in the relevant PARA folder
- Be descriptive but concise

## Linking

- Use Obsidian `[[wikilinks]]` syntax: `[[Note Title]]`
- Link to related notes at the bottom of each note
- Index notes are lists of `[[wikilinks]]`

## Workflows

### Search for notes

```bash
# Search by filename
find wiki/ -name "*.md" | grep -i "keyword"

# Search by content
grep -rl "keyword" wiki/ --include="*.md"
```

Or use Grep/Glob tools directly on the `wiki/` path.

### Create a new note

1. Determine the correct PARA folder
2. Use **Title Case** for the filename (e.g., `My Note.md`)
3. Write the content
4. Add `[[wikilinks]]` to related notes at the bottom
5. If an index note should link to this, update the index

### Find related notes

Search for `[[Note Title]]` across the vault to find backlinks:

```bash
grep -rl "\\[\\[Note Title\\]\\]" wiki/
```

### Find index notes

```bash
find wiki/ -name "*Index*"
```
