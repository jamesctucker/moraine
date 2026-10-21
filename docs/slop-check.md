# Slop check — code-quality measurement

Moraine ships a deterministic code-quality gate, `scripts/workspace/slop-check.py`, adapted from [SlopCodeBench](https://arxiv.org/abs/2603.24755) (a study showing coding agents degrade codebases monotonically over long-horizon iterative work — and that fresh context doesn't fix it, because the degradation lives in the workspace, not the conversation).

It measures two things:

- **Erosion** — how much of the codebase's complexity mass sits in functions with cyclomatic complexity over 10. High erosion means change is getting expensive.
- **Verbosity** — the share of lines flagged by a small ast-grep rule pack (swallowed exceptions, trivial wrappers, bool-if-return, etc.) or copied from elsewhere in the repo (clones). High verbosity means the code is padded.

Both are computed per repo and per diff. Missing or unmeasurable values are recorded as `null`, never imputed.

## First run: freeze your baselines

```bash
python3 scripts/workspace/slop-check.py --all --write
```

This snapshots every repo under `work/` plus `scripts/workspace` into `memory/eval/slop/snapshots/<month>/`. These are *your* reference points — the template ships no baselines, because they belong to your repos.

**Read bands as reference points, not gates.** The absolute green/warn/red bands come from the paper's human-vs-agent population means. A repo above the band is not a failure — it's a measurement. What matters is the *delta*: is this repo getting worse, and how fast?

## Grandfathering legacy repos

Imported a messy legacy repo? Don't let its inherited score cry wolf forever. List it in `slop-check.json` at the workspace root:

```json
{
  "grandfathered": ["my-legacy-repo"]
}
```

Grandfathered repos are **delta-gated only**: their absolute band never fails, but they still may not get *worse* faster than human velocity.

## The milestone gate (step 4b)

`implement-milestone` runs a structure check on every milestone diff:

```bash
python3 scripts/workspace/slop-check.py --range <base>..HEAD --repo <repo> --fail-on-new-cc
```

- **Blocking:** a diff that introduces a *new* callable with CC > 10 exits 1. The fix is to extract the seam first in a separate commit, then add the feature. This is the one blocking rule — in the upstream rehearsal it was the sharpest, lowest-noise signal.
- **Advisory:** Δerosion and Δverbosity are reported in the PR comment but never block on their own.

The matching write-time rules live in `AGENTS.md` (the anti-slop checklist) and `implement-milestone` step 3 (extract-before-extend: never add a branch to a function already over CC 10 or 60 lines). The checklist and the gate share a vocabulary: write code you wouldn't flag.

## Weekly sweep

`scheduled/slop-sweep.yaml` runs the full `--all --write` sweep every Monday and appends a flag-only report to the daily note. A repo is flagged when its weekly Δ exceeds human velocity (erosion +0.0053, verbosity +0.0022 per checkpoint, from the paper) — meaning it's slopping faster than a human would, which points at agent activity.

Install with the other cron jobs:

```bash
bun run .opencode/cron/runner.ts --install-defaults
```

## Detector health

`agent-eval.py` includes three golden tasks that keep the measurement honest:

- `slop-rules-valid` — every rule YAML parses
- `slop-fixture-clean` — a vendored clean file must stay clean (catches false positives)
- `slop-fixture-sloppy` — a vendored sloppy file must stay flagged (catches detector rot)

Run after any change to the rule pack or the script: `python3 scripts/workspace/agent-eval.py`.

## Tool dependencies

- `lizard` (complexity) — run via `uvx --from lizard==1.24.1`, or install it
- `ast-grep` (rule pack) — `brew install ast-grep` or see its docs
- `jscpd` (clones) — run via `npx -y jscpd@5.4.2`, or install it

Missing tools degrade gracefully: the corresponding half of verbosity is skipped and recorded as unavailable, not zero.
