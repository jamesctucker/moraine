# Agent Eval — Quality Baseline

This directory tracks the agent evaluation harness results. The harness (`scripts/workspace/agent-eval.py`) runs the core golden tasks plus any contributed by enabled packs, to verify the workspace is functional and discoverable.

## Structure

- `results/YYYY-Wnn.md` — Weekly evaluation results with per-task pass/fail and score trend

## Golden tasks

Five are core; the rest ship in the pack that owns them and run only while that pack is enabled. A core-only workspace scores 5/5; enabling the `quality` pack makes it 8/8.

**Core (always run):**

| Task | What it checks |
|------|---------------|
| `license-exists` | `LICENSE` exists and contains MIT text |
| `validate-passes` | `validate.py` exits 0 |
| `session-search-works` | a known two-file index returns structured results and never accepts the no-match response |
| `gitattributes-exists` | `.gitattributes` exists |
| `editorconfig-exists` | `.editorconfig` exists |

**Pack-contributed (quality pack, `packs/quality/eval.py`):**

| Task | What it checks |
|------|---------------|
| `slop-rules-valid` | every slop rule parses and scans successfully |
| `slop-fixture-clean` | the clean fixture has zero erosion and verbosity |
| `slop-fixture-sloppy` | the sloppy fixture exceeds the verbosity threshold |

A pack contributes tasks by exporting `TASKS` from `packs/<name>/eval.py`; the harness discovers it generically from the enabled-pack list.

## Usage

```bash
bash scripts/setup --yes                         # provision the workspace-local .venv
.venv/bin/python scripts/workspace/agent-eval.py # run every enabled task
.venv/bin/python scripts/workspace/agent-eval.py --history
```

The slop tasks also require `ast-grep`, `uvx`, and `npx` on `PATH` (see `packs/quality/docs/slop-check.md`). The session-search task builds its own fixture, so a fresh clone needs no existing memory index.
