# Contributing to Moraine

Thanks for considering a contribution. Moraine is a personal-workspace template, so contributions that help other people run it on their own machines are the best fit.

## Getting started

```bash
git clone https://github.com/jamesctucker/moraine
cd moraine
bash scripts/setup --yes
```

See the [README](README.md) for what Moraine is and the [first-session walkthrough](docs/first-session.md) for how it behaves.

## Making changes

1. Fork or branch, then make your change with tests.
2. Run the full gate before opening a PR:

   ```bash
   bun run test                                # Vitest (cron runner, hooks)
   .venv/bin/python -m pytest tests/ -q        # Pytest (workspace scripts)
   .venv/bin/ruff check tests/ scripts/       # Lint
   .venv/bin/python scripts/workspace/validate.py
   ```

3. Keep the same style as the surrounding code. Workspace scripts are plain Python 3.11+ with stdlib + PyYAML; cron code is TypeScript run under Bun.
4. Open a PR against `main` using the PR template.

## What's in scope

- **Bug fixes** for the setup script, cron runner, workspace scripts, skills, and docs.
- **Documentation corrections** — accuracy matters more than breadth here.
- **New deterministic checks** and improvements to existing workspace tooling, with tests.
- **Platform support** — anything that makes setup/first-session work on more machines.

## What's out of scope (for now)

- Hosted or multi-user anything.
- Sandboxing claims — OpenCode permission rules are not an OS sandbox.
- New bundled third-party skill packs (they expand the license/review surface).

## Reporting bugs

Use the bug-report issue template. Include the setup smoke-test output and the output of `.venv/bin/python scripts/workspace/validate.py` when relevant — deterministic output beats prose.

## Security

See [SECURITY.md](SECURITY.md). Don't open public issues for anything sensitive.
