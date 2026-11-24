# Changelog

All notable changes to Moraine are documented here.

Moraine was previously Joinery, and before that OpenBench (`github.com/jamesctucker/joinery` and `github.com/jamesctucker/openbench` — both redirect here). Entries for releases before those renames describe the same project under the old names.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **`moraine` CLI** (`scripts/moraine`) — `moraine sync [--dry-run]` makes the workspace match `moraine.yaml`: skill symlinks in `.agents/skills/`, the managed block in `.git/info/exclude`, the `mcp.servers` block of `.opencode/opencode.json`, and `~/.moraine/cron/enabled.json` for the job runner. `moraine packs list|enable <name>|disable <name>` manages the enabled-pack list. Sync never installs anything and never touches a real skill folder.
- **Manifest schema checks in `validate.py`** — `moraine.yaml` and every `packs/<name>/pack.yaml` are validated against the strict schema (unknown packs, requires cycles, harness fit, MCP name collisions); `--manifests` runs just that check.
- **Sync drift check in `health-check.py`** — runs the sync plan in dry-run mode, warns with the exact fix command when changes are pending, and errors on manifest problems. Runs in `--quick` mode too.
- **A `core-only` CI job** — git + Python only, no bun or Node on the runner: `setup --yes`, sync with no packs, validate, health-check, core pytest, and the core eval. The full job enables every pack and additionally runs vitest, the Bun timeout tests, the runner typecheck, and the npm pin check.

### Changed

- **Breaking: core needs only git and Python 3.11+.** Setup is core-first: it checks git and Python, creates the `.venv`, asks which harnesses you run (detected ones are the default, OpenCode installs only if chosen and missing, via bun or npm at the pinned `@opencode/cli` version), offers pack presets (core / recommended / everything / custom), shows each enabled pack's missing prerequisites with the exact install command, writes `moraine.yaml`, runs `moraine sync`, and smoke-tests. `--yes` is core with detected harnesses and installs nothing. bun, husky, and Vitest are contributor-only (see `CONTRIBUTING.md`).

- **Breaking: skills are core plus packs.** Skills moved from `.opencode/skills/<category>/<name>/` to a flat layout. Seven core skills are real folders in `.agents/skills/<name>/`: `create-skill`, `domain-modeling`, `grilling`, `scaffold-project`, `session-handoff`, `session-search`, `sync-upstream`. The other 23 moved into `packs/<pack>/skills/<name>/`, each pack described by its own `pack.yaml`: `engineering` (13 skills), `reflection` (3), `writing` (5), `design` (1), `obsidian` (1). `moraine.yaml` at the root lists your harnesses and enabled packs. Skills you write belong in `packs/local/skills/`. There is no migration tooling: if you edited a shipped skill, `git log --follow <new path>` finds its history.
- **`create-skill` writes to `packs/local/skills/`** and links the new folder into `.agents/skills/` with `moraine sync`, instead of writing into `.opencode/skills/`.
- **`sync-upstream`** classifies paths for the new layout, treats `moraine.yaml` and `packs/local/` as user-owned, and never writes to a user-owned path. For `opencode.json` it takes upstream's changes outside `mcp.servers` and leaves that block to `moraine sync`.
- **Impeccable** refers to its helper scripts at `.agents/skills/impeccable/scripts/`.
- **Pack scripts, tests, and docs moved into their packs.** `slop-check.py`, `slop-rules/`, `slop-fixtures/`, and `docs/slop-check.md` now live under `packs/quality/`; `memory-promoter.py` under `packs/reflection/scripts/`; `verify-deploy-vars.py` under `packs/engineering/scripts/` — each with its tests under the pack's `tests/`. The `slop-sweep` job moved to `packs/quality/jobs/` (installed only while both `quality` and `automation` are enabled). Invoke the scripts at their new paths.
- **Eval is core plus packs.** `agent-eval.py` runs five core golden tasks plus any `TASKS` contributed by enabled packs (`packs/<name>/eval.py`); the three slop tasks now come from the `quality` pack, so a core-only workspace scores 5/5 (8/8 with `quality` enabled). Core eval names no pack.
- **`AGENTS.md` slimmed to core** (~70 lines, harness-neutral): scheduled jobs moved to `packs/automation/AGENTS.md`, Headroom to `packs/headroom/`, issue tracking to `packs/engineering/` (which keeps the `[CUSTOMIZE]` tracker section), Semble search guidance to `packs/semble/`, and every pack now has its own `AGENTS.md`. Core files name no pack's skill or script unless the line says the pack is enabled; `tests/test_skill_references.py` enforces the boundary.
- **Pack tests run with the suite** — pytest collects `packs/` alongside `tests/`, and ruff lints it.
- **The cron runner moved to `packs/automation/runner/`** (with its `package.json`, lockfile, `tsconfig`, and `cron.config.yaml`; logs land in `packs/automation/.logs`). The runner's `--install-defaults` reads `~/.moraine/cron/enabled.json` (written by `moraine sync`) instead of scanning `scheduled/`, and removes installed job files that a pack shipped but no longer has enabled. `weekly-recap` now ships as the automation pack's own job (`packs/automation/jobs/`) and renders its PDF via `bun run --cwd packs/automation/runner render:pdf`. The runner's tests moved to `packs/automation/tests/` with the vitest config at `packs/automation/vitest.config.ts`.
- **`update-impeccable.sh` moved to `packs/design/scripts/`** and **`obsidian-audit` to `packs/obsidian/scripts/`** — invoke them at their new paths.
- **`health-check.py` no longer checks node** — node is the `quality` pack's prerequisite, not a core tool; the check moved out with the pack.
- **`.opencode/opencode.json` ships an empty `mcp.servers`** — `moraine sync` owns the block and fills it from the enabled packs (Semble and Headroom each ship their server in their pack).
- **A corrupt `enabled.json` stops the runner instead of uninstalling everything** — an unparseable job list was read as "no jobs", which made `--install-defaults` remove every installed shipped job; it now fails loudly before touching files. A missing file still means "sync has not run".
- **Two packs shipping the same job filename is now a sync error** — the runner installs job files by name alone, so a shared filename silently overwrote; sync refuses with both paths named, like skill ID collisions.
- **`health-check.py` checks packages in the interpreter running it** — the import checks use `sys.executable` (often the `.venv` python) instead of a bare `python3` from PATH, which may have nothing installed.

### Removed

- **The `scope: work` model gate** in the cron runner, pending a design for employer data. Jobs have no `scope` key and the cron config has no `work_models` allowlist. The job schema is now strict: a job file that still sets `scope:` fails validation with a message naming the key, instead of the key being silently ignored.
- **`scripts/mcp-servers/brave-search-mcp.sh`** — the wrapper pinned an npm package nobody imported; no server references it.

## [0.3.0] - 2026-11-21

Consolidates the October 2026 restructuring (OpenBench → Joinery → Moraine, config migration, setup review) with the November distribution-compliance, correctness, and release work. The June 2026 entry below remains 0.2.0.

### Added

- **Third-party provenance and licenses** — `THIRD_PARTY_NOTICES.md` inventories imported skills, exact upstream snapshots, and local adaptations. Missing Apache/MIT/CC BY-SA notices are restored alongside the relevant bundles, and vendored paths are marked for GitHub language statistics.
- **`docs/first-session.md`** — a 20-minute guided first session with the steps, the expected artifacts, a definition of done (the agent recalls yesterday unprompted), and a checklist for when recall fails.
- **Credentials check in the setup smoke test** — runs `opencode auth list` and points at `opencode auth login` instead of letting a fresh clone reach a login wall.
- **"What not to commit" policy** in the README and `AGENTS.md` — `memory/`, `wiki/`, and `artifacts/` are committed, so customer data, PII, credentials, and NDA material stay out.
- **Employer-data boundary** in the README and `AGENTS.md` — Moraine is for personal workspaces; employer-confidential code, customer data, credentials, and NDA material do not belong in it. The docs state plainly that deterministic scanning is a backstop for known secret patterns and cannot identify arbitrary confidential prose or source code.
- **Community and contribution files** — `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, a bug-report issue template, and a PR checklist.
- **README adoption surface** — CI badge, explicit supported-platform statement (macOS developed/tested, Ubuntu in CI, Windows untested), a short roadmap, and a trust-model section: review upstream skills/config before syncing, permission rules are not a sandbox, provider/MCP data policies apply.
- **7 skills**: `retro`, `prototype`, `wayfinder`, `wizard`, `teach`, `to-questionnaire`, `research`.
- **`code-review`** — two-axis review (Standards + Spec) from Matt Pocock's upstream skills repo, copied verbatim.
- **`next-artifact.py`** — allocates the next artifact number and can claim it safely under concurrent sessions (`--claim <slug>`).
- **Health-check table in `AGENTS.md`** mapping each deterministic script to when it should run.
- **15 skills synced from the upstream workspace**: `brainstorming`, `domain-modeling`, `executing-plans`, `find-skills`, `i-have-adhd`, `orchestrate-build-chain`, `pdf`, `tdd`, `writing-plans`, plus the four `readwise/` skills (`build-persona`, `feed-catchup`, `reader-recap`, `triage`) with shared `REFERENCE.md`/`SETUP.md` docs. (Upstream's `poetry-craft`, `wtf`, `ios-simulator`, `swiftui-pro`, and `swift-testing-pro` were intentionally left out as too workflow-specific.)
- **Workspace tooling**: `memory-audit.py`, `validate-repos.py`, `verify-deploy-vars.py`, `frontmatter.py` in `scripts/workspace/`; `weekly-recap.yaml` scheduled job (memory audit + week-in-review → daily note, optional email).

### Changed

- **Version metadata unified at 0.3.0** — `package.json` (was 0.2.0) and `pyproject.toml` (was 0.1.0) now match this release.
- **Documentation accuracy pass** — the "plain markdown" claim narrowed to the knowledge stores (tooling is Python/TypeScript/shell); both shipped scheduled jobs documented (`weekly-recap` and `slop-sweep`); Headroom's 60–95% savings figure attributed to Headroom's own docs; "no cloud dependency" replaced with an accurate statement (no Moraine-hosted backend; your provider and integrations are external services); ejection steps now cover `~/.moraine/cron/` and Headroom's MCP registration; Headroom setup points at `scripts/setup` or isolated `uv`/`pipx` installs instead of system `pip`; the upstream-sync `[CUSTOMIZE]` preservation language softened to a reviewed convention; session-handoff's memory commit is disclosed in onboarding.
- **Runtime and test dependencies** — Brave Search and Semble downloads are exactly pinned, weekly PDF rendering uses the locked `.opencode` package without Chromium's `--no-sandbox`, and Vitest/Vite moved to 4.1.11/7.3.7. Dependabot version updates are configured for Bun, pip, and GitHub Actions.
- **CI hardening** — workflow actions are pinned to full commit SHAs with workflow-level `permissions: contents: read`; Ruff now lints `scripts/workspace/` as well as `tests/`.
- **Config migrated to OpenCode V2** — `.opencode/opencode.json` now uses the native V2 shape (`mcp.servers`, `disabled` instead of `enabled`, ordered `permissions` array). `.opencode-version` pinned to `2.1.1`.
- **Shell-safety guardrails added** — destructive commands (`rm -rf /`, `dd` to block devices, `mkfs`/`mkswap`/`fdisk`, fork bombs, disk overwrites) are denied; `sudo`, `rm -rf ~`/`$HOME`, and remote-pipe-to-shell ask first; `external_directory` writes ask first.
- **Skills refresh** — 11 skills updated to current upstream versions (`diagnose`, `grilling`, `linearize`, `orchestrate-build-chain`, `impeccable`, `review-memory`, `session-search`, `brainstorming`, `improve-codebase-architecture`, plus new `ADR-FORMAT.md`/`CONTEXT-FORMAT.md` companions for `grilling`).
- **`domain-modeling` replaced** — track `GLOSSARY.md` (was `CONTEXT.md`) with `GLOSSARY-FORMAT.md`; dropped `CONTEXT-FORMAT.md` and the unused `agents/` config.
- **`setup` reads the OpenCode version from either output shape** (`2.1.1` or `opencode v2.1.1`) so the pin check no longer always prompts a reinstall; MCP trim and the Linear opt-in now edit `mcp.servers`.
- **`validate-repos.py`** gains opt-in machine scoping (`machine_scope` frontmatter) so one registry can span several machines.
- **RTK → Headroom migration** — replaced RTK (Rust Token Killer) with Headroom for context compression: installed `headroom-ai[mcp]`, registered the MCP server with OpenCode, uninstalled the `rtk` binary, deleted `.opencode/plugins/rtk.ts`, and rewrote the Token Efficiency docs and setup section.
- **Upstream sync pass** — carried-over skills synced to current upstream versions with personal examples genericized; stale skills removed (`token-compress`, `session-trace`, `executive-function`, `grill-me`); stale scheduled jobs removed (`morning-briefing`, `weekly-review`, `space-session-sync` — replaced by `weekly-recap`); test suite synced; `validate.py` wikilink checks skip imported Readwise content and Daily Notes (~1,100 fewer noise warnings); `scripts/mcp-servers/` trimmed to `brave-search-mcp.sh`; cron runner, CI, and dotfiles synced.
- **README** — skill count corrected to 34 (was miscounted as 35).
- **Renamed Joinery → Moraine.** Repo, package names, clone URLs, and the cron install path (`~/.joinery/cron/` → `~/.moraine/cron/`). Nothing about the workspace itself changed. If you had cron jobs installed under the old path, re-run `bun run .opencode/cron/runner.ts --install-defaults` to install them at the new one. Missing/invalid cron config also falls back to `~/.moraine/cron/` now, not `~/.garage/cron/`.
- **Renamed OpenBench → Joinery** (earlier the same day). Repo, package names, clone URLs, and the cron install path (`~/.openbench/cron/` → `~/.joinery/cron/`).
- **README rewritten for onboarding** — problem-first framing, a `For / Not for` fit check, the four-store model (work / memory / wiki / artifacts), install with provider-auth prerequisites, a first-20-minutes activation loop, and verify commands. The fork-sync guide moved to `docs/upstream-sync.md`; the deep file tree is trimmed to the eight entries that teach the model.
- **`linearize` renamed to `to-issue` and made tracker-agnostic** — same propose-then-create workflow and `Route: rote|creative` tag, but it no longer assumes Linear tool names, a 0–4 priority scale, a hardcoded team key, or the initiative → project → issue model. It names the operations and defers to whichever tracker MCP is configured. `orchestrate-build-chain`, `implement-milestone`, `AGENTS.md`, and the setup featured-skills list follow the new name.
- **`to-issue` now slices tracer bullets** — borrowed from Matt Pocock's `to-tickets`: every proposal row states the end-to-end behaviour it delivers, carries a `Blocked by` edge, and is sized to one context window; wide refactors get the expand–contract treatment instead of a fake vertical slice. Issues are published blockers-first so the edges reference real IDs.

### Fixed

- **Memory tooling safety and correctness** — staging topics cannot escape the project directory; same-date manual decisions survive index regeneration; nested skills are discovered; frontmatter delimiters are line-aware; missing skill frontmatter and child audit failures are reported accurately. Auto-promoted project notes now arrive with the required `next-action` frontmatter and a `projects.md` index row instead of immediately violating workspace conventions.
- **Session search rebuilds are atomic** — the FTS index is built in a temporary database and swapped into place, so a failed or concurrent rebuild can no longer leave searchers querying an empty or half-populated index.
- **`verify-deploy-vars --repo` confines scans to `work/`** — absolute, nested, and traversing repo names are rejected before any file is read.
- **Artifact validation accepts numbers past 99** — allocation and validation agree on the `NNN-` prefix convention.
- **Slop measurement integrity** — weekly snapshots use ISO dates, retain same-day history by default, and compare against the latest earlier snapshot. The CC gate compares callable identities, and detector/Git failures no longer look like clean results.
- **Cron safety** — lock ownership, process-group timeout escalation, atomic output writes, job-name/schedule validation, and email header handling now cover concurrent and adversarial cases.
- **Validation and evaluation** — MCP health checks inspect the real server configuration, the eval builds a deterministic search fixture and runs all eight tasks, and pre-push fails closed when required tools are absent. CI also typechecks the cron runner.
- **Workflow references** — bundled skills use shipped Moraine workflows, numbered artifacts, and the shared `GLOSSARY.md` convention instead of missing dependencies. Static tests reject broken local links and unshipped references.
- **The CI Node job never ran the tests.** `npm ci` and `setup-node`'s npm cache both need an npm lockfile, and `package-lock.json` is gitignored — so the job failed at setup on every push. It now installs from the committed `bun.lock`, installs `.opencode/` dependencies (the cron runner imports `yaml`, `zod`, and `marked` from there), and runs vitest under the Node version in `.nvmrc`.
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

- **Bundled PDF skill** — removed because its upstream license prohibited redistribution. The optional weekly-recap PDF export still uses the separately packaged `md-to-pdf` tool.
- **Experimental sandbox helpers** — `scripts/sandbox/opencode-sandbox` and `scripts/sandbox/pii-scan` are outside the initial public release. No sandbox or Seatbelt behavior is advertised or required.
- **`spaces/`** — the domain-consultant space system is gone: the template and `spaces/README.md`, the `scripts/spaces/` loader and session-sync script, and the `/use-space` command. Persistent domain context belongs in a skill (which auto-loads on intent) or in `AGENTS.md`, not in a directory you have to load by hand.
- **`readwise/` skills** (`build-persona`, `reader-recap`, `triage`, plus the shared `REFERENCE.md` and `SETUP.md`) — the Readwise MCP server is no longer shipped, so the whole category is gone. Skill count 34 → 31.
- **Readwise, Granola, and Linear MCP integrations** — dropped from `.opencode/opencode.json`, the README integrations list, and the setup script (the Linear opt-in flow is gone). Only Semble and Headroom ship configured; add your own tracker, reader, or meeting-notes server to `opencode.json` when you want it.
- **9 retired skills**: `find-skills`, `space-loader`, `command-policy`, `grill-with-docs`, `mcp-scaffold`, `obsidian-audit`, `feed-catchup`, `perplexity-research`, and the `ux/web-design-guidelines` skill (the `ux/` category is gone).
- **Sunsama MCP integration** — dropped from `opencode.json`, setup trim menu, and docs.

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
- Moraine Cron scheduler (`scripts/workspace/cron-runner.py`) (#15)
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
