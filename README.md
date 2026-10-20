# OpenBench

**A git-backed workspace your coding agent can remember.**

Every session with a coding agent starts from zero: it doesn't know your projects, your conventions, or what you decided last week. OpenBench closes that gap with a repo the agent reads on startup — project notes, session summaries, decisions — plus skills that encode how work gets done here.

**For:** engineers who use a coding agent daily and are tired of re-explaining context.
**Not for:** teams wanting one shared workspace (each person clones their own; code stays in its own repos under `work/`), or anyone wanting a hosted service.

## The four stores

Four directories, four jobs. The split is the point: the agent writes memory, you write the wiki.

| Directory | What lives there | Who writes it |
|-----------|------------------|---------------|
| `work/` | Code repos, each independently versioned | you + agent |
| `memory/` | What happened, decisions, next actions | agent |
| `wiki/` | Durable knowledge — PARA (projects, areas, resources, archives) | you |
| `artifacts/` | Designs, research, specs, plans | agent |

```
openbench/
├── AGENTS.md          # agent instructions and conventions
├── memory/            # agent-written session context
├── wiki/              # your PARA vault (open in Obsidian)
├── artifacts/         # designs, research, specs
├── work/              # your code repos
├── scripts/           # setup + workspace tooling
├── scheduled/         # cron job definitions
└── .opencode/         # config, cron runner, skills
```

Everything outside `work/` is plain markdown in one git repo, so the agent's context is reviewable, diffable, and yours.

## Install

### Prerequisites

- `git`, `bun`, `python3` 3.11+
- A model provider for OpenCode. Setup installs OpenCode; the credentials are yours:

  ```bash
  opencode auth login          # Anthropic, DeepSeek, OpenRouter, …
  opencode auth list           # confirm something is stored
  ```

### Setup

```bash
git clone https://github.com/jamesctucker/openbench
cd openbench
bash scripts/setup
```

Consent-first: nothing is installed outside the workspace without a prompt, and every prompt shows the exact command. Setup checks your tools, installs OpenCode at the pinned version (`.opencode-version`), installs JS deps and Python deps into a workspace-local `.venv/` (never system Python), optionally installs Headroom and Obsidian, lets you trim MCP servers, and runs a smoke test that includes a credentials check. `--yes` accepts defaults non-interactively.

### Verify

```bash
.venv/bin/python scripts/workspace/validate.py       # structure, skills, links
.venv/bin/python scripts/workspace/health-check.py   # workspace sanity
bun run test                                         # Vitest — cron runner, hooks
.venv/bin/python -m pytest                           # Pytest — workspace scripts
```

Use `python3` instead of `.venv/bin/python` only if you installed the Python deps elsewhere.

### Obsidian (optional)

`wiki/` is an Obsidian vault. Open it in the Obsidian desktop app (not the repo root) to browse, edit, and follow wikilinks.

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

## Your first 20 minutes

Onboarding has one test: **in a second session, the agent recalls what you did in the first without being told.**

1. **Scaffold a project.** Start `opencode` in the repo root and say *"Scaffold a project called Checkout."* The `scaffold-project` skill creates the wiki top note and the index row.
2. **Do one small piece of work.** *"Add a health endpoint to Checkout, with a test."* Steer as it goes; that's normal.
3. **Wrap up.** *"Wrap up this session."* The `session-handoff` skill writes `memory/sessions/<date>-*.md` and updates `memory/index.md`.
4. **Prove recall.** Start a fresh session and ask *"What did I work on yesterday, and what's the next step?"*

If step 4 works, onboarding worked. [Full walkthrough with expected output →](docs/first-session.md)

## Daily workflow

```
# Morning: agent reads context, you set direction
Agent reads memory/index.md → active projects, recent decisions, open threads
You: "Let's continue the auth refactor in work/my-app"
Agent reads work/my-app/AGENTS.md → stack, conventions, deploy notes
Agent reads memory/staging/2026-06-15.md → restart anchors from yesterday

# Work: agent codes, researches, documents
Agent implements, runs tests, commits
Agent writes thinking to memory/staging/ with restart anchors
You jump in with feedback; agent adapts

# Wrap-up: agent summarizes
session-handoff writes memory/sessions/ and updates memory/index.md
You're done. Context survives until tomorrow.
```

Finding past context:

```bash
.venv/bin/python scripts/workspace/session-index.py search "authentication decision"
```

For code across repos, ask the agent — the Semble MCP server searches `work/` semantically.

## Automation and integrations

### Scheduled jobs

A lightweight cron scheduler runs automated agent tasks. It ships with one job, `weekly-recap` (Mondays 8am): a deterministic memory audit plus a week-in-review appended to your daily note. Jobs are YAML files in `scheduled/`; copy `weekly-recap.yaml` to add your own.

```bash
bun run .opencode/cron/runner.ts --install-defaults   # install jobs to ~/.openbench/cron/
bun run .opencode/cron/runner.ts --list               # list configured jobs
bun run .opencode/cron/runner.ts --dry-run            # see what would fire now
bun run .opencode/cron/runner.ts --once weekly-recap  # run one immediately
```

Add it to crontab (every minute is fine — it only fires when a job's schedule matches):

```
* * * * * cd /path/to/openbench && bun run .opencode/cron/runner.ts
```

```yaml
name: my-job
cron: "0 8 * * 1-5"     # every weekday at 8am
prompt: "Read memory/staging/ and produce a morning briefing."
skills:                  # optional — skills the agent should load
  - session-search
hostname: my-machine     # optional — restrict to one machine
```

### MCP servers

Configured in `.opencode/opencode.json`. Two ship enabled:

- **Semble** — semantic code search across `work/` repos (local, `uvx`).
- **Headroom** — context compression, 60–95% fewer tokens on tool output, reversible via CCR (local).

Add your own tracker, reader, or meeting-notes server there when you want it; `to-issue` and the other skills will use whatever the agent can see.

### Built on

| Project | Role |
|---------|------|
| [OpenCode](https://github.com/anomalyco/opencode) | Agentic coding agent and skill platform |
| [Semble](https://github.com/MinishLab/semble) | Semantic code search with model2vec embeddings |
| [SQLite FTS5](https://www.sqlite.org/fts5.html) | Full-text search for session search |
| [Obsidian](https://obsidian.md) | PARA knowledge vault (human-curated side) |
| [Headroom](https://github.com/headroomlabs-ai/headroom) | Context compression (60–95% savings, reversible via CCR) |

## Make it yours

OpenBench is cloned, not hosted. Everything is in git — memory, wiki, skills, project repos. No signup, no cloud dependency, no vendor lock-in.

- **`AGENTS.md`** — the main lever: conventions, commands, issue tracking, remote access.
- **`.opencode/skills/`** — 32 skills. Edit them, or write your own with the `create-skill` skill.
- **`.opencode/opencode.json`** — MCP servers and shell-safety permissions.
- **The loop** — sessions feed reviews, reviews feed new skills, skills improve future sessions. It gets more useful the longer you use it.

### What not to commit

`memory/` and `wiki/` are committed to git on purpose — that's what makes the context portable. Treat them like a shared notebook:

- **Never paste** customer data, PII, credentials, incident details, or NDA material into `memory/`, `wiki/`, or `artifacts/`.
- Keep secrets in `.env` (gitignored) and reference them by name in notes.
- If you need a private scratch space, keep it out of the repo or in a separate private clone.

### Staying in sync

Pull upstream improvements without losing your customization:

```bash
git remote add upstream https://github.com/jamesctucker/openbench.git
git fetch upstream && git merge upstream/main
```

Or just tell the agent *"Sync with upstream"* — the `sync-upstream` skill classifies changes, preserves your `[CUSTOMIZE]` sections, and commits with a rollback branch. Details, conflict tips, and what's safe to merge: [docs/upstream-sync.md](docs/upstream-sync.md).

## License

MIT — see [LICENSE](LICENSE).
