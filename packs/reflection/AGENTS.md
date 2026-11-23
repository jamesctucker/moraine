# Reflection pack

Looking back: memory reviews, single-session retros, and promoting recurring notes.

## Skills

- `review-memory` — analyze recent session summaries to find repeated workflows, manual patterns, and automation opportunities.
- `retro` — post-session retrospective on the agent's environment: navigation gaps, missing automated checks, steering no-ops, token waste, and information blind spots, ranked by severity.
- `memory-promoter` — review `memory/staging/` periodically and promote recurring entries to wiki project notes or session summaries.

`memory-audit.py` (core) flags stale staging and overdue reviews; the fixes for both live here.

## Scripts

- `scripts/memory-promoter.py` — the deterministic half of the `memory-promoter` skill: finds recurring staging entries and promotion candidates. `--dry-run` (default) reports only.
