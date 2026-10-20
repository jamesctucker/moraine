---
name: memory-promoter
description: Review memory/staging/ periodically and promote recurring entries to wiki project notes or session summaries. Use when asked to clean up staging, find promotion candidates, or surface recurring topics. For pattern analysis across sessions use review-memory; for finding a specific past discussion use session-search.
---

# Memory Promoter

Reviews `memory/staging/` for topics referenced across 3+ distinct days and promotes them to `wiki/1 Projects/` (project notes). Session summary promotion requires manual agent judgment using the candidate report.

## When to use

- User asks "anything in staging worth promoting?"
- User asks "clean up my staging notes"
- User asks "what topics keep coming up?"
- During session wrap-up or weekly review

## Workflow

### 1. Dry-run (default — report only)

```bash
python scripts/workspace/memory-promoter.py
```

Prints a table of promotion candidates: topic, mention count, and whether already promoted. No files are created.

### 2. Promote (auto-create wiki project notes)

```bash
python scripts/workspace/memory-promoter.py --promote
```

Creates `wiki/1 Projects/<topic>/00 Top Note.md` for candidates that aren't already promoted.

### 3. Review the report

The report is written to `memory/staging/promotion-candidates-YYYY-MM-DD.md`. Read it to see what was promoted.

## How it works

- Scans all `memory/staging/YYYY-MM-DD.md` files (skips `README.md`, `health-check-*`, and `promotion-candidates-*`)
- Extracts topics from: `##` headings, wikilinks (`[[...]]`), project references (`project: X`), and backlinks (`see also: X`)
- Counts distinct days each topic appears
- Topics appearing on 3+ distinct days are candidates
- `--promote` creates a minimal wiki top note for each candidate

## Promotion criteria

A staging entry should be promoted when it:
- References the same project/topic across 3+ distinct days
- Has enough context to form a project note or session summary
- Isn't already tracked in `wiki/1 Projects/` or `memory/sessions/` (the script checks this mechanically)
- Is still relevant and actionable (agent judgment required)

The script handles the mechanical check; the agent should still exercise judgment before promoting (e.g., checking if the topic is still relevant).
