# OpenBench

A personal workspace for building projects, storing documents, and running agentic AI workflows with OpenCode.

## What's in here

- `wiki/` — PARA knowledge management vault (human-written). Open this folder as an Obsidian vault for the human side of knowledge management.
- `memory/` — agent session summaries, staging, and reviews (agent-written)
- `work/` — independently versioned project repos (each subdir is its own git repo)
- `artifacts/` — research, architecture docs, design plans
- `spaces/` — reusable domain consultant prompts
- `scripts/` — tooling (MCP servers, workspace scripts, sandbox wrappers)
- `scheduled/` — cron job YAMLs for automated agent tasks
- `.opencode/` — OpenCode config, skills, plugins, cron runner

## Setup

```bash
git clone <this-repo>
cd openbench
bash scripts/setup
```

Requires: `git`, `bun`, `python3`. The setup script auto-installs `uv` (Python package manager) and `opencode` (versioned via `.opencode-version`). It installs all workspace deps, offers to install `headroom` (context compression) and `obsidian` (wiki client), lets you trim unwanted MCP servers, runs a smoke test, and prints featured skills to try first.

Next: edit `AGENTS.md` to match your project tracking setup, edit `.opencode/opencode.json` to enable/disable MCP servers, open `wiki/` as an Obsidian vault, and start OpenCode in the repo root.

### Obsidian (wiki client)

The `wiki/` directory is an Obsidian vault. Open it in the Obsidian desktop app (not the repo root) to browse, edit, and follow wikilinks.

```bash
# macOS
brew install --cask obsidian
# Linux (Flatpak)
flatpak install flathub md.obsidian.Obsidian
# Windows
winget install Obsidian.Obsidian
# Or download from https://obsidian.md
```

Then: open Obsidian → "Open folder as vault" → select `wiki/`.

## Integrations

MCP servers configured in `.opencode/opencode.json`:

- **Granola** — meeting notes and voice memo integration (remote MCP, no setup)
- **Sunsama** — daily planning and task management (remote MCP, no setup). The `executive-function` skill pairs well with Sunsama.
- **Readwise** — highlights and Reader access (remote MCP, no setup)
- **Semble** — semantic code search across `work/` repos (local server, `uvx`)
- **Headroom** — context compression (local server, save 60-95% on tool output tokens)

See `AGENTS.md` for the full directory map and agent conventions.

## Keeping your fork up to date

Add upstream as a remote:

```bash
git remote add upstream https://github.com/jamesctucker/openbench.git
```

Fetch and merge:

```bash
git fetch upstream
git merge upstream/main
```

GitHub also has a "Sync fork" button in the UI (`https://github.com/<you>/openbench` → Fetch upstream).

### What to expect when syncing

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
- `spaces/` — your custom spaces
- `artifacts/` — your artifacts

### Conflict tips

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

### Agent-assisted sync

Instead of merging manually, ask OpenCode to sync for you:

> Sync with upstream

The `sync-upstream` skill handles the whole flow: classifies changes (safe vs. personalized vs. user-owned), auto-merges structural files, smart-merges your `[CUSTOMIZE]` sections in AGENTS.md and `opencode.json`, runs a smoke test, and commits with a backup branch you can roll back to. It's the magical version of the manual flow above.
