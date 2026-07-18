# OpenBench

A personal workspace for building projects, storing documents, and running agentic AI workflows with OpenCode.

## What's in here

- `wiki/` — PARA knowledge management vault (human-written)
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

Requires: `git`, `bun`, `python3`. The setup script auto-installs `uv` (Python package manager) and `opencode` (versioned via `.opencode-version`). It installs all workspace deps, offers to install `headroom` (context compression), lets you trim unwanted MCP servers, runs a smoke test, and prints featured skills to try first.

Next: edit `AGENTS.md` to match your project tracking setup, edit `.opencode/opencode.json` to enable/disable MCP servers, and start OpenCode in the repo root.

## Integrations

MCP servers configured in `.opencode/opencode.json`:

- **Granola** — meeting notes and voice memo integration (remote MCP, no setup)
- **Sunsama** — daily planning and task management (remote MCP, no setup). The `executive-function` skill pairs well with Sunsama.
- **Readwise** — highlights and Reader access (remote MCP, no setup)
- **Semble** — semantic code search across `work/` repos (local server, `uvx`)
- **Headroom** — context compression (local server, save 60-95% on tool output tokens)

See `AGENTS.md` for the full directory map and agent conventions.
