# Agent Eval — Quality Baseline

This directory tracks the agent evaluation harness results. The harness (`scripts/workspace/agent-eval.py`) runs a set of golden tasks to verify the workspace is functional and discoverable.

## Structure

- `results/YYYY-Wnn.md` — Weekly evaluation results with per-task pass/fail and score trend

## Golden tasks

| Task | What it checks |
|------|---------------|
| `license-exists` | `LICENSE` exists and contains MIT text |
| `validate-passes` | `validate.py` exits 0 |
| `session-search-works` | a known two-file index returns structured results and never accepts the no-match response |
| `gitattributes-exists` | `.gitattributes` exists |
| `editorconfig-exists` | `.editorconfig` exists |
| `slop-rules-valid` | every slop rule parses and scans successfully |
| `slop-fixture-clean` | the clean fixture has zero erosion and verbosity |
| `slop-fixture-sloppy` | the sloppy fixture exceeds the verbosity threshold |

## Usage

```bash
bash scripts/setup --yes                         # provision the workspace-local .venv
.venv/bin/python scripts/workspace/agent-eval.py # run all eight tasks
.venv/bin/python scripts/workspace/agent-eval.py --history
```

The slop tasks also require `ast-grep`, `uvx`, and `npx` on `PATH` (see `docs/slop-check.md`). The session-search task builds its own fixture, so a fresh clone needs no existing memory index.
