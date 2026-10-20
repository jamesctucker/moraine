# Keeping your fork up to date

Joinery is a template. You clone it, personalize it, and pull upstream improvements later. This page is the manual flow; the `sync-upstream` skill automates all of it.

## Add upstream

```bash
git remote add upstream https://github.com/jamesctucker/joinery.git
```

## Fetch and merge

```bash
git fetch upstream
git merge upstream/main
```

GitHub also has a "Sync fork" button in the UI (`https://github.com/<you>/joinery` → Fetch upstream).

## What to expect when syncing

**Safe to merge (rarely conflict):**

- `scripts/` — setup, MCP servers, workspace tooling
- `.opencode/skills/` — skill definitions
- `.opencode/cron/` — cron runner
- `tests/` — test suite
- `.husky/` — git hooks
- `scheduled/` — cron job YAMLs
- `.opencode-version` — OpenCode version pin
- `package.json`, `requirements.txt` — dependency manifests

**Expect conflicts (you've likely personalized these):**

- `AGENTS.md` — issue tracker config, remote access, conventions
- `README.md` — setup notes, integrations
- `.opencode/opencode.json` — MCP server selection
- `wiki/` — your PARA vault content
- `memory/` — session summaries, staging notes
- `artifacts/` — your artifacts

## `[CUSTOMIZE]` markers

Files like `AGENTS.md` contain HTML-comment markers:

```html
<!-- [CUSTOMIZE] Configure your issue tracker below. ... -->
```

Sections wrapped in these markers are intentionally generic placeholders you replace with your own setup. The `sync-upstream` skill treats them as merge-protected — when upstream changes the surrounding scaffolding, your customized sections are preserved. If you sync by hand, just be aware these marked regions are yours; everything else is upstream-owned.

## Conflict tips

If a file has nothing but local changes you don't want to keep:

```bash
git checkout upstream/main -- path/to/file
```

This discards your version and takes upstream's. Useful when upstream ships a fix to `scripts/setup` and you haven't personalized it.

If a file is heavily personalized and you want to keep your version:

```bash
git merge --abort                          # bail on the merge
git cherry-pick <upstream-commit-sha>      # take only the specific fix you want
```

When in doubt, `git merge --abort` and inspect with `git diff upstream/main -- path/to/file` before deciding.

## Agent-assisted sync

Instead of merging manually, ask OpenCode to sync for you:

> Sync with upstream

The `sync-upstream` skill handles the whole flow: classifies changes (safe vs. personalized vs. user-owned), auto-merges structural files, smart-merges your `[CUSTOMIZE]` sections in `AGENTS.md` and `opencode.json`, runs a smoke test, and commits with a backup branch you can roll back to. It's the magical version of the manual flow above.
