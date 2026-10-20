# OpenBench

**A personal workspace for developers who work with AI agents.**

OpenBench is where your knowledge, agent sessions, and project workspace live together in one git repository — with independently versioned project repos in `work/`. It gives you a PARA-organized wiki for knowledge management, persistent agent memory across sessions, reusable agent skills, and MCP-powered integrations — all in a structure you clone, fork, and make your own.

## What a session looks like

```
# Morning: agent reads context, you set direction
Agent reads memory/index.md → sees active projects, recent decisions, open threads
You: "Let's continue the auth refactor in work/my-app"
Agent reads work/my-app/AGENTS.md → learns stack, conventions, deploy notes
Agent reads memory/staging/2026-06-15.md → picks up restart anchors from yesterday

# Work: agent codes, researches, documents
Agent implements changes, runs tests, commits
Agent writes thinking to memory/staging/ with restart anchors
You jump in with feedback; agent adapts

# Wrap-up: agent summarizes
session-handoff skill writes summary to memory/sessions/
Updates memory/index.md with new decisions and next actions
You're done. Context survives until tomorrow.
```

## 30-second demo

```bash
# Clone and set up
git clone https://github.com/jamesctucker/openbench
cd openbench
bash scripts/setup

# Validate everything works
python scripts/workspace/validate.py
python scripts/workspace/health-check.py

# Start a session
opencode

# Search past sessions (once you have some)
python scripts/workspace/session-index.py search "authentication decision"

# Search code across repos (via the agent's semble_search MCP tool)
#   → agent: "find the payment flow in work/"

# Wrap up
# (session-handoff skill handles this automatically)
```

## Scheduled jobs

OpenBench includes a lightweight cron scheduler that runs automated agent tasks. It ships with one job, `weekly-recap` (Mondays 8am): a deterministic memory audit plus a week-in-review appended to your daily note. Job definitions live in `scheduled/` as simple YAML files — copy `weekly-recap.yaml` to add your own. The runner is TypeScript, executed via [`bun`](https://bun.sh/).

```bash
# Install default jobs to ~/.openbench/cron/
bun run .opencode/cron/runner.ts --install-defaults

# List all configured jobs
bun run .opencode/cron/runner.ts --list

# Dry-run: see what would fire right now
bun run .opencode/cron/runner.ts --dry-run

# Run a single job immediately (ignores cron schedule)
bun run .opencode/cron/runner.ts --once weekly-recap
```

Add `bun run .opencode/cron/runner.ts` to your crontab (every minute is fine — it only fires when a job's schedule matches):

```
* * * * * cd /path/to/openbench && bun run .opencode/cron/runner.ts
```

Job files use a simple format:

```yaml
name: my-job
cron: "0 8 * * 1-5"     # every weekday at 8am
prompt: "Read memory/staging/ and produce a morning briefing."
skills:                  # optional — skills the agent should load
  - session-search
hostname: my-machine     # optional — restrict to a specific machine
```

## Structure

```
openbench/
├── README.md               # You are here
├── AGENTS.md               # Agent instruction file
├── CHANGELOG.md            # Keep a Changelog
├── LICENSE                 # MIT
├── .gitattributes          # Cross-platform line endings
├── .editorconfig           # Project formatting baseline
├── .nvmrc                  # Node version pin
├── .opencode-version       # OpenCode version pin
├── package.json            # Bun tooling (vitest, husky)
├── pyproject.toml          # Ruff config, pytest config
├── requirements.txt        # Python deps
├── .github/workflows/      # CI pipeline (pytest + vitest + ruff + validate)
├── .husky/                 # Pre-push hook: pytest + ruff + vitest
├── scheduled/              # Cron job definitions (YAML)
│   └── weekly-recap.yaml
├── scripts/                # CLI tools and automation
│   ├── setup               # Workspace setup and onboarding
│   ├── workspace/          # validate, health-check, session-index, memory-audit, project-status, agent-eval
│   ├── mcp-servers/        # MCP server implementations (e.g. brave-search)
│   ├── sandbox/            # opencode-sandbox, pii-scan
├── tests/                  # pytest + vitest test suites
├── wiki/                   # PARA knowledge vault (open as an Obsidian vault)
│   ├── 1 Projects/         # projects.md index + top notes with YAML frontmatter
│   ├── 2 Areas/            # ongoing responsibilities + areas.md index
│   ├── 3 Resources/
│   └── 4 Archives/
├── memory/                 # Agent session summaries and context
│   ├── index.md            # Entry point: active projects, open threads
│   ├── sessions/           # Per-session summaries and handoffs
│   ├── staging/            # Short-term working memory
│   ├── reviews/            # Pattern analysis from review-memory
│   ├── work-repos.md       # Persistent context about repos
│   ├── historical-decisions.md  # Decision blocks archived out of index.md
│   ├── eval/               # Agent evaluation results
│   └── .index/             # SQLite FTS5 search indexes (gitignored)
├── artifacts/              # Architecture docs, research, design plans
├── work/                   # External project repos (each independently versioned)
└── .opencode/              # OpenCode configuration
    ├── opencode.json       # MCP servers
    ├── cron.config.yaml    # Cron runner config
    ├── cron/               # TypeScript cron runner + modules
    └── skills/             # Agent skill definitions (auto-discovered, 32 skills)
```

## Integrations

MCP servers are configured in `.opencode/opencode.json`. Each is opt-in — setup shows the list and lets you trim any you don't want.

- **Semble** — semantic code search across `work/` repos (local server, `uvx`).
- **Headroom** — context compression (local server, save 60–95% on tool output tokens, reversible via CCR).

See `AGENTS.md` for the full directory map and agent conventions.

## Setup

```bash
git clone https://github.com/jamesctucker/openbench
cd openbench
bash scripts/setup
```

Requires: `git`, `bun`, `python3` (3.11+). The setup script is consent-first: nothing is installed outside the workspace without a prompt, and every prompt shows the exact command that will run. It checks for `opencode` (versioned via `.opencode-version`, offers `bun install -g opencode-ai` if missing), installs workspace JS deps and Python deps (into a workspace-local `.venv/` — never system Python), optionally installs `headroom` (context compression) and `obsidian` (wiki client), lets you trim unwanted MCP servers, runs a smoke test, and prints featured skills to try first. Pass `--yes` to accept defaults non-interactively (CI).

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

## Built on

| Project | Role |
|---------|------|
| [OpenCode](https://github.com/anomalyco/opencode) | Agentic coding agent and skill platform |
| [Semble](https://github.com/MinishLab/semble) | Semantic code search with model2vec embeddings |
| [SQLite FTS5](https://www.sqlite.org/fts5.html) | Full-text search engine for session search |
| [Obsidian](https://obsidian.md) | PARA knowledge vault (human-curated side) |
| [Headroom](https://github.com/headroomlabs-ai/headroom) | Context compression (60–95% savings, reversible via CCR) |

## Fork it, make it yours

OpenBench is designed to be cloned and customized. Everything is in git — your memory, your wiki, your skills, your project repos. There's no signup, no cloud dependency, no vendor lock-in.

- **Use it as-is** — clone, run setup, start working.
- **Fork it** — change the conventions, swap the MCP servers, write your own skills.
- **Build on it** — the architecture documents in `artifacts/` are designed to be extended.

The self-improving loop means the workspace gets smarter the more you use it. Sessions feed reviews. Reviews feed new skills. Skills improve future sessions. Over time, the workspace adapts to how you work.

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

## License

MIT — see [LICENSE](LICENSE).

---

*Built with OpenCode and a philosophy that your workspace should work for you, not the other way around.*
