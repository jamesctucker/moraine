# Automation pack

Scheduled agent jobs: the cron runner, the weekly recap, email delivery, and PDF rendering. OpenCode-only — the runner starts every job with `opencode run`.

## Cron runner

The runner lives in this pack, at `packs/automation/runner/` (TypeScript under Bun; its dependencies install there too). Job definitions are YAML files in the `jobs/` folders of this and other enabled packs, plus your own in `packs/local/jobs/`. `moraine sync` writes the enabled list to `~/.moraine/cron/enabled.json`; the runner installs from that list:

```bash
bun run packs/automation/runner/runner.ts --install-defaults   # install enabled jobs to ~/.moraine/cron/
bun run packs/automation/runner/runner.ts --list               # list all jobs
bun run packs/automation/runner/runner.ts --once weekly-recap  # run one immediately
```

`--install-defaults` also removes installed job files that a pack shipped but no longer has enabled.

Add to crontab (runs every minute, fires only when schedule matches). Set PATH explicitly — cron's default excludes `~/.bun/bin` and `~/.opencode/bin`, so without it the job silently never runs:

```
PATH=$HOME/.bun/bin:$HOME/.opencode/bin:/usr/local/bin:/usr/bin:/bin
* * * * * cd /path/to/moraine && bun run packs/automation/runner/runner.ts
```

## Jobs

- `weekly-recap` (Mondays 8am, `jobs/weekly-recap.yaml`) — runs the deterministic memory audit, then appends a week-in-review to the daily note; optional email delivery via the commented `email:` block in the job file.
- Jobs shipped by other enabled packs (for example the quality pack's `slop-sweep`) install through the same runner, from the same enabled list.

## Prerequisites

`bun` and `opencode` — see `pack.yaml` for install commands. This pack's harnesses is `[opencode]`; `moraine packs enable automation` refuses unless `opencode` is listed in `moraine.yaml`.
