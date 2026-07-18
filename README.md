# OpenBench

A personal workspace for working with AI agents that actually remember.

## The problem

AI coding agents are powerful, but they have no memory between sessions. Every conversation starts from scratch. Your project context, your decisions, your research — it all resets when you close the terminal. Existing tools either:

- **Claude Code** — Great at code, but no cross-session memory, no knowledge management, no integrations.
- **OpenHuman** — Auto-fetches everything from 118+ services. Powerful, but agent-centric: it decides what matters, not you.
- **Hermes Agent** — A monolithic runtime with browser automation and media generation. Powerful scope, heavy install.
- **OpenWork** — A polished desktop app with multi-platform reach. Company-backed, YC-funded. Different scale entirely.

OpenBench takes a different approach: **workspace-centric, not agent-centric.** You organize your knowledge (PARA wiki). You decide what's a project, what's an area, what's archive. The agent reads from and writes to that structure on your terms. Memory is just markdown in git — readable by you, diffable, portable. No database, no lock-in.

## How it's different

| Dimension | OpenBench | OpenHuman | Hermes Agent | OpenWork | Claude Code |
|-----------|-----------|-----------|--------------|----------|-------------|
| **Philosophy** | Workspace-centric. You curate; the agent assists. | Agent-centric. Agent auto-fetches and populates. | Agent-centric. Monolithic runtime. | Desktop app. Company-backed. | Coding tool. Stateless sessions. |
| **Knowledge management** | Full PARA + Obsidian vault with wikilinks, frontmatter, audit | Obsidian vault as auto-populated view | None | None | None |
| **Memory** | git-native markdown: sessions, staging, reviews, per-repo memory | Memory Tree with auto-fetch | SQLite + JSON session history | Session history only | No cross-session memory |
| **Skills** | 28 curated, deep, workspace-aware | Skill system with auto-fetch context | Skill marketplace | ~15 infrastructure-focused | No skill system |
| **Integrations** | 6 intentional MCP servers (Granola, Sunsama, Readwise, Linear, Semble, Headroom) — opt-in, not auto-fetch | 118+ via Composio (auto-fetch) | 70+ built-in tools | Extension manifest system | No integrations |
| **Install** | `git clone` + `bash scripts/setup` | `npx openhuman` | `pip install hermes` + API keys | Desktop download | `npm install -g @anthropic-ai/claude-code` |
| **Audience** | Developer/thinker/founder who wants deep, structured work | User who wants agent to "just know" everything | Power user who wants broad tool coverage | Team/enterprise seeking multi-platform | Developer who wants AI in their editor |
| **Open source** | MIT | GNU GPL-3.0 | Apache 2.0 | MIT | Proprietary |

## What a session looks like

```
# Morning: agent reads context, you set direction
Agent reads memory/index.md → sees active projects, recent decisions, open threads
You: "Let's continue the auth refactor in work/my-app"
Agent reads work/my-app/AGENTS.md → learns stack, conventions, deploy notes
Agent reads memory/staging/2026-07-17.md → picks up restart anchors from yesterday

# Work: agent codes, researches, documents
Agent implements changes, runs tests, commits
Agent writes thinking to memory/staging/ with restart anchors
You jump in with feedback; agent adapts

# Wrap-up: agent summarizes
session-handoff skill writes summary to memory/sessions/
Updates memory/index.md with new decisions and next actions
You're done. Context survives until tomorrow.
```

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

Requires: `git`, `bun`, `python3`. The setup script auto-installs `uv` (Python package manager) and `opencode` (versioned via `.opencode-version`). It installs all workspace deps, offers to install `headroom` (context compression) and `obsidian` (wiki client), lets you trim unwanted MCP servers, offers to enable `linear` (issue tracking), runs a smoke test, and prints featured skills to try first.

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

### Linear (optional, issue tracking)

Linear is configured as a remote MCP server (no local install). It's **disabled by default** — enable it in setup or by editing `.opencode/opencode.json`. On first use, OpenCode prompts for OAuth; sign in once and the agent can read issues, create projects, update status, and link PRs.

The `linearize` skill converts specs, artifacts, or repos into Linear structure: it reads the source, proposes a breakdown table (issue → label → project → priority), waits for your approval, then creates everything with cross-links back to the source. Try it with: *"linearize artifacts/15-payment-gateway-integration.md"*.

## Integrations

MCP servers configured in `.opencode/opencode.json`:

- **Granola** — meeting notes and voice memo integration (remote MCP, no setup)
- **Sunsama** — daily planning and task management (remote MCP, no setup). The `executive-function` skill pairs well with Sunsama.
- **Readwise** — highlights and Reader access (remote MCP, no setup)
- **Linear** — issue tracking (remote MCP, disabled by default — enable in setup or opencode.json). The `linearize` skill converts specs/repos to Linear issues.
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

### `[CUSTOMIZE]` markers

Files like `AGENTS.md` contain HTML-comment markers:

```html
<!-- [CUSTOMIZE] Configure your issue tracker below. ... -->
```

Sections wrapped in these markers are intentionally generic placeholders you replace with your own setup. The `sync-upstream` skill treats them as merge-protected — when upstream changes the surrounding scaffolding, your customized sections are preserved. If you sync by hand, just be aware these marked regions are yours; everything else is upstream-owned.

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
