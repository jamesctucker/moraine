# Moraine

[![CI](https://github.com/jamesctucker/moraine/actions/workflows/ci.yml/badge.svg)](https://github.com/jamesctucker/moraine/actions/workflows/ci.yml)

**A git-backed workspace your coding agent can remember.**

Every session with a coding agent starts from zero: it doesn't know your projects, your conventions, or what you decided last week. Moraine closes that gap with a repo the agent reads on startup — project notes, session summaries, decisions — plus skills that encode how work gets done here.

**For:** engineers who use a coding agent daily and are tired of re-explaining context.
**Not for:** teams wanting one shared workspace (each person clones their own; code stays in its own repos under `repos/`), or anyone wanting a hosted service.

## The four stores

Four directories, four jobs. The split is the point: the agent writes memory, you write the wiki.

| Directory | What lives there | Who writes it |
|-----------|------------------|---------------|
| `repos/` | Code repos, each independently versioned and registered as pointers | you + agent |
| `memory/` | What happened, decisions, next actions | agent |
| `wiki/` | Durable knowledge — PARA (projects, areas, resources, archives) | you |
| `artifacts/` | Designs, research, specs, plans | agent |

```
moraine/
├── AGENTS.md          # agent instructions and conventions
├── memory/            # agent-written session context
├── wiki/              # your PARA vault (open in Obsidian)
├── artifacts/         # designs, research, specs
├── repos/             # your code repos (registered in repos/README.md)
├── scripts/           # setup, the moraine CLI, core workspace tooling
├── .agents/skills/    # core skills + one symlink per enabled pack skill
├── packs/             # opt-in packs: skills, scripts, jobs (automation's cron runner lives here)
├── moraine.yaml       # which harnesses and packs you enabled
└── .opencode/         # OpenCode config (permissions, MCP servers)
```

Everything the agent needs for context — `memory/`, `wiki/`, `artifacts/` — is plain markdown in one git repo, so it is reviewable, diffable, and yours. (`scripts/` and `packs/` hold the Python/TypeScript/shell tooling that keeps it that way.)

## Install

### Prerequisites

- `git` and `python3` 3.11+ — that is all core needs
- A model provider for your harness (Anthropic, DeepSeek, OpenRouter, …). Setup offers to install OpenCode at the pinned version; you authenticate after setup, below.
- Optional, per pack: `bun` (only if you enable the `automation` pack's cron runner), the Obsidian app (obsidian pack), and the tools each pack's `pack.yaml` lists as prerequisites.

**Platforms:** developed and tested on macOS; the full test suite and workspace validation also run on Ubuntu Linux in CI. Windows is untested — use WSL if you try it.

### Setup

```bash
git clone https://github.com/jamesctucker/moraine
cd moraine
bash scripts/setup
```

Setup is core-first: it checks git and Python, creates a workspace-local `.venv/`, asks which agent harnesses you run (detected ones are the default), and offers pack presets — **core**, **recommended** (engineering + reflection + semble), **everything**, or **custom** per pack. For every enabled pack it shows missing prerequisites with the exact install command from that pack's `pack.yaml`, and installs nothing without a prompt. It writes your choices to `moraine.yaml`, runs `moraine sync` to link the pack skills and MCP servers, and smoke-tests the result.

If you chose OpenCode, authenticate your provider — setup installed the CLI, but the credentials are yours:

```bash
opencode auth login          # Anthropic, DeepSeek, OpenRouter, …
opencode auth list           # confirm something is stored
```

`--yes` accepts defaults non-interactively (CI): core with the harnesses detected on PATH, nothing installed.

### Point origin at your own repo

The clone's `origin` is the public template — but your memory, wiki, and project notes are committed to git, so they need somewhere to go. Create a private repo and repoint `origin`:

```bash
gh repo create moraine --private    # or create one in the GitHub UI
git remote set-url origin <your-repo-url>
```

Forking first and cloning your fork works too. Either way, pulling template updates later is covered in [docs/upstream-sync.md](docs/upstream-sync.md).

### Verify

```bash
.venv/bin/python scripts/workspace/validate.py       # structure, skills, links
.venv/bin/python scripts/workspace/health-check.py   # workspace sanity
.venv/bin/python -m pytest                           # Pytest — core + pack scripts
```

Vitest (the automation pack's cron-runner tests) needs bun and the root `node_modules` — contributor-only; core users can skip it.

Use `python3` instead of `.venv/bin/python` only if you installed the Python deps elsewhere.

### Obsidian (optional)

`wiki/` is an Obsidian vault. Open it in the Obsidian desktop app (not the repo root) to browse, edit, and follow wikilinks (`[[links]]` between notes).

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
3. **Wrap up.** *"Wrap up this session."* The `session-handoff` skill writes `memory/sessions/<date>-*.md`, updates `memory/index.md`, and commits those memory writes (scoped to `memory/` paths — it never sweeps unrelated changes into the commit).
4. **Prove recall.** Start a fresh session and ask *"What did I work on in my last session, and what's the next step?"*

If step 4 works, onboarding worked. You'll know: the agent answers from its own reading — naming the project, what you did, and the next step — without you pasting anything. [Full walkthrough with expected output →](docs/first-session.md)

## Daily workflow

```
# Morning: agent reads context, you set direction
Agent reads memory/index.md → active projects, recent decisions, open threads
You: "Let's continue the auth refactor in repos/my-app"
Agent reads repos/my-app/AGENTS.md → stack, conventions, deploy notes
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

For code across repos, ask the agent — the Semble MCP server searches the paths in `repos/` semantically.

## Automation and integrations

Moraine is harness-neutral: OpenCode, Claude Code, and Codex read the same `AGENTS.md` and skills. One exception — the cron runner below starts every job with `opencode run`, so the `automation` pack needs OpenCode.

### Scheduled jobs

A lightweight cron scheduler runs automated agent tasks. It ships in the `automation` pack (`packs/automation/runner/`, TypeScript under Bun). Jobs are YAML files in each pack's `jobs/` folder and your own in `packs/local/jobs/` — two ship: `weekly-recap` (Mondays 8am — a deterministic memory audit plus a week-in-review appended to your daily note) and the quality pack's `slop-sweep` (Mondays 9am — weekly code-quality measurement across your `repos/` repos, flag-only). `moraine sync` writes the enabled list to `~/.moraine/cron/enabled.json`; the runner installs from it.

```bash
bun run packs/automation/runner/runner.ts --install-defaults   # install enabled jobs to ~/.moraine/cron/
bun run packs/automation/runner/runner.ts --list               # list configured jobs
bun run packs/automation/runner/runner.ts --dry-run            # see what would fire now
bun run packs/automation/runner/runner.ts --once weekly-recap  # run one immediately
```

Add it to crontab (every minute is fine — it only fires when a job's schedule matches). Set PATH explicitly: cron's default excludes `~/.bun/bin` and `~/.opencode/bin`, so without this line the job silently never runs:

```
PATH=$HOME/.bun/bin:$HOME/.opencode/bin:/usr/local/bin:/usr/bin:/bin
* * * * * cd /path/to/moraine && bun run packs/automation/runner/runner.ts
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

MCP servers (tool integrations the agent can call) are configured per pack: enabling a pack adds its servers to your harness's config via `moraine sync`. Two packs ship them — **Semble** (semantic code search across the paths in `repos/`, local, `uvx`) and **Headroom** (context compression, reversible via CCR). Add your own in `moraine.yaml`'s `mcp:` block; `to-issue` and the other skills use whatever the agent can see.

### Built on

| Project | Role |
|---------|------|
| [OpenCode](https://github.com/anomalyco/opencode) | Agentic coding agent and skill platform |
| [Semble](https://github.com/MinishLab/semble) | Semantic code search with model2vec embeddings |
| [SQLite FTS5](https://www.sqlite.org/fts5.html) | Full-text search for session search |
| [Obsidian](https://obsidian.md) | PARA knowledge vault (human-curated side) |
| [Headroom](https://github.com/headroomlabs-ai/headroom) | Context compression (its own docs report 60–95% savings, reversible via CCR) |

## Make it yours

Moraine is cloned, not hosted. Everything is in git — memory, wiki, skills, project repos. No Moraine-operated backend and no signup. Your selected model provider and any MCP integrations you enable are external services with their own data policies, and the bundled automation currently targets OpenCode — memory itself stays portable Markdown you can read without any tool.

- **`AGENTS.md`** — the main lever: conventions, commands, issue tracking, remote access.
- **`.agents/skills/` and `packs/`** — 7 core skills and 23 more in packs. Enable packs in `moraine.yaml`, edit them, or write your own with the `create-skill` skill.
- **`.opencode/opencode.json`** — shell-safety permissions; `moraine sync` writes the `mcp.servers` block.
- **The loop** — sessions feed reviews, reviews feed new skills, skills improve future sessions. It gets more useful the longer you use it.

### Ejecting

Everything Moraine-specific lives in the clone, but a few things do land outside it:

- Cron state: installed jobs live under `~/.moraine/cron/` and the crontab line you added runs the runner.
- OpenCode and Headroom: whatever you let setup install globally (`opencode`, `headroom`, Obsidian), plus Headroom's MCP registration in your OpenCode config if you accepted it.

To remove it all: delete the clone directory, remove the crontab line and `~/.moraine/`, run `headroom mcp uninstall` (if registered), and uninstall the global tools you opted into.

### What not to commit

`memory/` and `wiki/` are committed to git on purpose — that's what makes the context portable. Treat them like a shared notebook:

- **Never paste** customer data, PII, credentials, incident details, or NDA material into `memory/`, `wiki/`, or `artifacts/`.
- Keep secrets in `.env` (gitignored) and reference them by name in notes.
- If you need a private scratch space, keep it out of the repo or in a separate private clone.

**Moraine is for personal workspaces.** Do not put employer-confidential code, customer data, credentials, or NDA material into it. Use it for work only in an employer-approved environment.

Deterministic scanning (secret scanning, credential hooks) is only a backstop: it catches known secret patterns, not arbitrary confidential prose or source code. The boundary above is the primary control.

### Staying in sync

Pull upstream improvements without losing your customization:

```bash
git remote add upstream https://github.com/jamesctucker/moraine.git
git fetch upstream && git merge upstream/main
```

Or just tell the agent *"Sync with upstream"* — the `sync-upstream` skill classifies changes and commits with a rollback branch. Details, conflict tips, and what's safe to merge: [docs/upstream-sync.md](docs/upstream-sync.md).

### Trust model

- **Review upstream skills and config before syncing.** Skills and config files are instructions your agent will follow — read the diff in a sync like you'd read a dependency update.
- **Permission rules are not a sandbox.** OpenCode's deny/ask lists guard commands, not OS-level file or network access.
- **Provider and MCP data policies apply.** Everything you or the agent sends through your model provider and MCP servers is governed by those services, not by Moraine.

## Roadmap

- More deterministic health checks over the memory/wiki structures the agent relies on.
- Easier exclusion of large third-party skill bundles, to shrink install and review surface.
- Cross-platform setup and first-session verification (currently macOS-tested, Linux-CI).

Ideas tracked in [issues](https://github.com/jamesctucker/moraine/issues).

## License

MIT for Moraine's original work — see [LICENSE](LICENSE). Bundled third-party components retain their own licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
