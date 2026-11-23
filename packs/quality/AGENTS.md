# Quality pack

Deterministic code-quality measurement (erosion and verbosity) for your repos. Flag-only: it reports, never modifies code or memory.

## Contents

- `scripts/slop-check.py` — measures erosion (complexity mass, via pinned lizard through `uvx`) and verbosity (ast-grep rule hits, pinned jscpd through `npx`). `--range` reports deltas, `--fail-on-new-cc` blocks new callables above CC 10, `--all --json --write` snapshots every repo under `memory/eval/slop/`.
- `scripts/slop-rules/` — the ast-grep rule set verbosity is measured against.
- `scripts/slop-fixtures/` — clean and sloppy golden fixtures.
- `docs/slop-check.md` — thresholds, bands, and how to read a report.
- `jobs/slop-sweep.yaml` — weekly snapshot sweep (Mondays 9am), installed only while the `automation` pack is also enabled.
- `eval.py` — contributes three golden tasks to `agent-eval.py`: rules parse, the clean fixture stays clean, the sloppy fixture stays flagged.

## Prerequisites

`uvx` (uv), `ast-grep`, and `node` — see `pack.yaml` for install commands. `moraine packs list` shows which are missing; sync never installs anything.

## When to run it

- Before/after big agent-built chains, and in milestone work as the step-4b structure gate.
- Weekly via the `slop-sweep` job (needs the `automation` pack).
- Grandfathered repos live in `slop-check.json` at the workspace root and are delta-gated only.
