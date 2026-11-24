# Obsidian pack

Browse and manage the wiki (`wiki/`) as an [Obsidian](https://obsidian.md) vault.

## Skills

- `obsidian-vault` — search, create, and organize notes in the vault with wikilinks and PARA placement.

## Conventions

- Opening `wiki/` in Obsidian creates a `.obsidian/` config directory on first open (gitignored) — per-user vault state stays out of git.
- `packs/obsidian/scripts/obsidian-audit` checks the vault for structural issues (broken wikilinks, stale frontmatter); run it from the workspace root.

The desktop app is optional: any text editor works on the same markdown. `moraine packs list` reports the Obsidian app as a missing prerequisite only when neither `obsidian` on PATH nor an installed app is found.
