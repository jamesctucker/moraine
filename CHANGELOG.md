# Changelog

All notable changes to OpenBench are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **`linearize` renamed to `to-issue` and made tracker-agnostic** — same propose-then-create workflow and `Route: rote|creative` tag, but it no longer assumes Linear tool names, a 0–4 priority scale, a hardcoded team key, or the initiative → project → issue model. It names the operations and defers to whichever tracker MCP is configured. `orchestrate-build-chain`, `implement-milestone`, `AGENTS.md`, and the setup featured-skills list follow the new name.
- **`to-issue` now slices tracer bullets** — borrowed from Matt Pocock's `to-tickets`: every proposal row states the end-to-end behaviour it delivers, carries a `Blocked by` edge, and is sized to one context window; wide refactors get the expand–contract treatment instead of a fake vertical slice. Issues are published blockers-first so the edges reference real IDs.

### Removed

- **`readwise/` skills** (`build-persona`, `reader-recap`, `triage`, plus the shared `REFERENCE.md` and `SETUP.md`) — the Readwise MCP server is no longer shipped, so the whole category is gone. Skill count 35 → 32.
- **Readwise, Granola, and Linear MCP integrations** — dropped from `.opencode/opencode.json`, the README integrations list, and the setup script (the Linear opt-in flow is gone). Only Semble and Headroom ship configured; add your own tracker, reader, or meeting-notes server to `opencode.json` when you want it.

## [0.2.0] - 2026-10-20

### Changed

- **Config migrated to OpenCode V2** — `.opencode/opencode.json` now uses the native V2 shape (`mcp.servers`, `disabled` instead of `enabled`, ordered `permissions` array). `.opencode-version` pinned to `2.1.1`.
- **Shell-safety guardrails added** — destructive commands (`rm -rf /`, `dd` to block devices, `mkfs`/`mkswap`/`fdisk`, fork bombs, disk overwrites) are denied; `sudo`, `rm -rf ~`/`$HOME`, and remote-pipe-to-shell ask first; `external_directory` writes ask first.
- **Skills refresh** — 11 skills updated to current upstream versions (`diagnose`, `grilling`, `linearize`, `orchestrate-build-chain`, `impeccable`, `review-memory`, `session-search`, `brainstorming`, `improve-codebase-architecture`, plus new `ADR-FORMAT.md`/`CONTEXT-FORMAT.md` companions for `grilling`).
- **`domain-modeling` replaced** — track `GLOSSARY.md` (was `CONTEXT.md`) with `GLOSSARY-FORMAT.md`; dropped `CONTEXT-FORMAT.md` and the unused `agents/` config.
- **`setup` reads the OpenCode version from either output shape** (`2.1.1` or `opencode v2.1.1`) so the pin check no longer always prompts a reinstall; MCP trim and the Linear opt-in now edit `mcp.servers`.
- **`validate-repos.py`** gains opt-in machine scoping (`machine_scope` frontmatter) so one registry can span several machines.
- **README** — skill count corrected to 35, `readwise/` skill list corrected to three.

### Added

- **7 skills**: `retro`, `prototype`, `wayfinder`, `wizard`, `teach`, `to-questionnaire`, `research`.
- **`code-review`** — two-axis review (Standards + Spec) from Matt Pocock's upstream skills repo, copied verbatim.
- **`next-artifact.py`** — allocates the next artifact number and can claim it safely under concurrent sessions (`--claim <slug>`).
- **Health-check table in `AGENTS.md`** mapping each deterministic script to when it should run.

### Removed

- **9 retired skills**: `find-skills`, `space-loader`, `command-policy`, `grill-with-docs`, `mcp-scaffold`, `obsidian-audit`, `feed-catchup`, `perplexity-research`, and the `ux/web-design-guidelines` skill (the `ux/` category is gone).

### Fixed

- **Setup script review pass** — correctness, consent, and platform fixes:
  - Wrong npm package for OpenCode auto-install (`opencode` → `opencode-ai`) — the install path previously always failed
  - No more silent installs: uv and OpenCode are now prompted with the exact install command shown (uv was previously installed via an unprompted `curl | sh`)
  - Python deps now install into a workspace-local `.venv/` (previously `uv pip install --system` mutated system Python); uv is optional, with a `python3 -m venv` + pip fallback
  - headroom installs via `uv tool`/`pipx`/venv fallback instead of system pip; MCP registration now explains what it writes
  - `node -e` → `bun -e` (script no longer depends on Node; previously crashed mid-run if the optional Node offer was declined)
  - Branch rename guarded to the only safe case (branch `master`, no `main`, not detached) — previously could crash under `set -e`
  - `fail()` now actually exits; exact (not substring) `.opencode-version` compare; Flatpak Obsidian detection (`-d` → `-e`); `~/Applications` checked on macOS
  - Python 3.11+ requirement enforced; smoke test adds `validate.py` and uses the venv interpreter; `--yes` non-interactive mode for CI

### Removed

- **Sunsama MCP integration** — dropped from `opencode.json`, setup trim menu, and docs.

### Changed

- **README rewritten** — restructured around the session lifecycle and 30-second demo (dropped the competitor comparison); integrations section now explains what Readwise and Granola are and why they're useful.

### Added

- **15 new skills** synced from the upstream workspace: `brainstorming`, `domain-modeling`, `executing-plans`, `find-skills`, `i-have-adhd`, `orchestrate-build-chain`, `pdf`, `tdd`, `writing-plans`, plus the four `readwise/` skills (`build-persona`, `feed-catchup`, `reader-recap`, `triage`) with shared `REFERENCE.md`/`SETUP.md` docs. (Upstream's `poetry-craft`, `wtf`, `ios-simulator`, `swiftui-pro`, and `swift-testing-pro` were intentionally left out as too workflow-specific.)
- **Workspace tooling**: `memory-audit.py`, `validate-repos.py`, `verify-deploy-vars.py`, `frontmatter.py` in `scripts/workspace/`; `weekly-recap.yaml` scheduled job (memory audit + week-in-review → daily note, optional email).

### Changed

- **Skills refresh** — all carried-over skills synced to current upstream versions; personal examples genericized (`my-app`, sample area names).
- **Removed stale skills**: `token-compress`, `session-trace`, `executive-function`, `grill-me` (dropped upstream; `i-have-adhd` is the successor to `executive-function`, `grilling` covers `grill-me`).
- **Removed stale scheduled jobs**: `morning-briefing`, `weekly-review`, `space-session-sync` (decommissioned upstream) — replaced by `weekly-recap`.
- **Tests** — suite synced with upstream (dropped `test_token_compress`/`test_session_frontmatter`, added `test_memory_audit` and cron runner tests).
- **`validate.py`** — wikilink checks skip imported Readwise content and Daily Notes (journal links are intentional forward references), cutting ~1,100 noise warnings.
- **Scripts** — `scripts/workspace/`, `sandbox/`, `spaces/`, `obsidian-audit` synced; `scripts/mcp-servers/` trimmed to `brave-search-mcp.sh` (stale goodreads package files removed).
- **Cron runner + CI + dotfiles** — synced with upstream (`.opencode/cron/`, `.github/`, `.husky/`, `pyproject.toml`, `requirements.txt`, `.gitignore`, `.gitattributes`, `.editorconfig`, `.nvmrc`).

### Changed

- **RTK → Headroom migration** — replaced RTK (Rust Token Killer) with Headroom for context compression:
  - Installed `headroom-ai[mcp]` via pip, registered MCP server with OpenCode
  - Uninstalled `rtk` binary via Homebrew, deleted `.opencode/plugins/rtk.ts`
  - Rewrote AGENTS.md Token Efficiency section (RTK → Headroom)
  - Updated README.md structure tree, Built on table, and Getting Started step
  - Replaced RTK install section in `scripts/setup` with Headroom section
- **README.md accuracy pass** — reconciled the README against current repo state after the cron-runner TypeScript migration and RTK integration:
  - Replaced all `python scheduled/cron-runner.py` commands with `bun run .opencode/cron/runner.ts` equivalents (Scheduled jobs section + crontab example)
  - Removed references to non-existent `feed-catchup.yaml` (prose + structure tree)
  - Replaced broken `semble search` CLI demo with MCP-tool invocation hint
  - Updated skills count from "~20" to "27"
  - Qualified Orchestrator Harness row as "(currently disabled)" in the comparison table
  - Added RTK to the "Built on" table and the Getting Started install step (`brew install rtk && rtk init -g --opencode`)
  - Rewrote the structure tree to reflect actual on-disk layout: removed `todos/` and phantom `cron-runner.py`; added `CHANGELOG.md`, `.nvmrc`, `package.json`, `pyproject.toml`, `requirements.txt`, `reader_persona.md`, `.husky/`, `tests/`, `memory/eval/`, and `.opencode/` subtree (`cron.config.yaml`, `cron/`, `plugins/`)
  - Verified `--dry-run` flag still supported by the TypeScript runner before re-listing it

## [0.2.0] — 2026-06-16

### Added

- **Agent 6 — CI & quality baseline** (#18–#22):
  - CI pipeline: GitHub Actions workflow with Python tests, lint, Node tests, and workspace validation (pytest + vitest + ruff) (#20)
  - Test suite: 85 pytest + 2 vitest covering lib, validate, token-compress, cron-runner, session-frontmatter, health-check, update-index (#18)
  - Developer tooling: `pyproject.toml` with ruff config, root `requirements.txt`, `.nvmrc`, Husky pre-push hook (#19)
  - Infrastructure: `.husky/` pre-push hook runs pytest + ruff before each push (#19)
  - Documentation: `CHANGELOG.md` with Keep a Changelog format, semantic versioning started at v0.1.0 (#21)
- **Agent 7 — Agent observability** (#23, #25, #26):
  - `memory-promoter` skill: scans `memory/staging/` for cross-referenced topics and promotes entries referenced 3+ times to wiki project notes (#23)
  - `agent-eval` harness: golden task set (8 tasks) with results tracking in `memory/eval/results/` and trend analysis (#25)
  - `session-trace` skill: produces structured timeline traces from session files with reasoning steps, decisions, tool calls, and artifact tracking (#26)

### Changed

- `.gitignore`: added `.pytest_cache/` exclusion

## [0.1.0] — 2026-06-15 (Phase 1 foundation)

> Retrospective: Phase 1 items were implemented in earlier commits before semantic versioning was established.
> This changelog entry captures the state of the workspace at the start of Phase 2.

### Added

- Session search indexer (`scripts/workspace/session-index.py`) with SQLite FTS5 (#13)
- Startup health check (`scripts/workspace/health-check.py`) (#14)
- OpenBench Cron scheduler (`scripts/workspace/cron-runner.py`) (#15)
- YAML frontmatter schema for sessions (`memory/.sessions-schema.yaml`) (#16)
- Memory index auto-updater (`scripts/workspace/update-index.py`)
- Token compressor skill (`scripts/workspace/token-compress.py`) (#6)
- Workspace structure validator (`scripts/workspace/validate.py`)
- Session frontmatter helper (`scripts/workspace/session-frontmatter.py`)
- Editing conventions (`AGENTS.md`, `.editorconfig`) (#17)
- Open source files: `LICENSE` (MIT), `SECURITY.md`, `CODE_OF_CONDUCT.md` (#1, #2, #3)
- GitHub templates: issue and PR templates (#12)
- Project documentation: `CONTRIBUTING.md`, `ARCHITECTURE.md`, `CLAUDE.md`, `llms.txt` (#7, #9, #10, #11)
- `README.md` rewrite with problem/philosophy/demo/comparison sections (#8)
- `.gitattributes` (#4)
- Skill ecosystem: `command-policy`, `token-compress`, plus 15+ existing skills (#5, #6)
- `session-search` skill (#13)
- Artifact AI authorship attribution convention (#47)
