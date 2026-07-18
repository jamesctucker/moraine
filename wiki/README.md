# Wiki — PARA Vault

Knowledge management using the PARA method. Humans write here; agents write to `memory/`.

This is an **Obsidian vault**. Open the `wiki/` folder (not the repo root) in the [Obsidian](https://obsidian.md) desktop app to browse, edit, and follow wikilinks. On first open, Obsidian creates a `.obsidian/` config directory (gitignored) — per-user vault state stays out of git.

If you haven't installed Obsidian yet:

```bash
# macOS
brew install --cask obsidian
# Linux (Flatpak)
flatpak install flathub md.obsidian.Obsidian
# Windows
winget install Obsidian.Obsidian
# Or download from https://obsidian.md
```

Then: Obsidian → "Open folder as vault" → select `wiki/`.

## Structure

- **0 Inbox** — captured items awaiting sorting
- **1 Projects** — active, paused, and completed project top notes (with YAML frontmatter)
- **2 Areas** — ongoing responsibilities (no finish line)
- **3 Resources** — topical reference material
- **4 Archives** — inactive material kept for reference

## Project top notes

Every project in `1 Projects/` should have a top note with YAML frontmatter:

```yaml
---
status: active | paused | completed
priority: low | medium | high | urgent
tags: []
next-action: ""
---
```

Index of all projects: `1 Projects/projects.md`.

## Conventions

- `0 Inbox/00 Scratchpad.md` is the human scratchpad — agents must never write to it.
- Wiki notes use Markdown + wikilinks.
- For agent session context, see `memory/`, not here.
