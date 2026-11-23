# Automation pack

Scheduled agent jobs: the cron runner, the weekly recap, email delivery, and PDF rendering. OpenCode-only — the runner starts every job with `opencode run`.

## Cron runner

Job definitions are YAML files in `scheduled/` (this workspace's) and in `jobs/` folders of enabled packs. The runner lives at `.opencode/cron/runner.ts`:

```bash
bun run .opencode/cron/runner.ts --install-defaults   # install jobs to ~/.moraine/cron/
bun run .opencode/cron/runner.ts --list               # list all jobs
bun run .opencode/cron/runner.ts --once weekly-recap  # run one immediately
```

Add to crontab (runs every minute, fires only when schedule matches). Set PATH explicitly — cron's default excludes `~/.bun/bin` and `~/.opencode/bin`, so without it the job silently never runs:

```
PATH=$HOME/.bun/bin:$HOME/.opencode/bin:/usr/local/bin:/usr/bin:/bin
* * * * * cd /path/to/moraine && bun run .opencode/cron/runner.ts
```

## Jobs

- `weekly-recap` (Mondays 8am) — runs the deterministic memory audit, then appends a week-in-review to the daily note; optional email delivery via the commented `email:` block in the job file.
- Jobs shipped by other enabled packs (for example the quality pack's `slop-sweep`) install through the same runner; `moraine sync` writes the enabled list to `~/.moraine/cron/enabled.json`.

## Prerequisites

`bun` and `opencode` — see `pack.yaml` for install commands. This pack's harnesses is `[opencode]`; `moraine packs enable automation` refuses unless `opencode` is listed in `moraine.yaml`.
