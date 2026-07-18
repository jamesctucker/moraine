---
name: sync-upstream
description: Sync this fork with the upstream OpenBench repo, preserving user personalizations. Use when user says "sync with upstream", "pull upstream changes", "update from upstream", or "keep my fork current".
---

# Sync with Upstream

## When to use

User wants to pull changes from the upstream OpenBench repo into their fork while preserving their personalizations (AGENTS.md customizations, MCP server selection, wiki content, etc.).

## Overview

This is a **merge** operation, not a reset. The goal is to take upstream improvements (new skills, script fixes, cron updates) while keeping the user's personal content intact. The agent does **semantic merging** for files with `[CUSTOMIZE]` markers and structural auto-merging for files that are pure upstream code.

## Pre-flight

### 1. Verify upstream remote

```bash
git remote get-url upstream
```

If this fails (missing remote), add it:

```bash
git remote add upstream https://github.com/jamesctucker/openbench.git
```

If the URL is different from `jamesctucker/openbench`, warn the user and ask if they want to update it.

### 2. Check working tree is clean

```bash
git status --porcelain
```

If anything is uncommitted or staged, stop and tell the user: "Working tree is dirty. Commit or stash your changes before syncing." Do not proceed.

### 3. Create a backup branch

This is the escape hatch — if the sync goes wrong, the user can always reset to this branch.

```bash
BACKUP_BRANCH="backup-pre-sync-$(date +%Y%m%d-%H%M%S)"
git branch "$BACKUP_BRANCH"
```

Tell the user: "Created backup branch `\"$BACKUP_BRANCH\"`. If anything goes wrong: `git reset --hard $BACKUP_BRANCH`"

### 4. Fetch upstream

```bash
git fetch upstream
```

### 5. Detect if there's anything to sync

```bash
git diff HEAD..upstream/main --name-only
```

If the output is empty, tell the user "Already up to date — no upstream changes to sync" and exit.

If there are changes, list them so the user sees what's coming:

```
Upstream changes detected:
  M  scripts/setup
  M  .opencode/skills/agent/session-handoff/SKILL.md
  A  .opencode/skills/engineering/new-skill/SKILL.md
  ...
```

## Classify changes

For each changed file, classify into one of three buckets based on the path:

### SAFE — structural files, auto-take upstream

These files are pure upstream code. The user should not have personalized them. If local changes exist, they were probably accidental.

- `scripts/**` (setup, MCP servers, workspace scripts, sandbox, spaces, obsidian-audit)
- `.opencode/skills/**` (skill definitions)
- `.opencode/cron/**` (cron runner code)
- `.opencode/plugins/**` (plugin scaffolding)
- `.opencode/package.json` (OpenCode dependencies)
- `.opencode-version`
- `tests/**`
- `.husky/**` (git hooks — but be careful, user might have customized hook content)
- `.github/**`
- `.editorconfig`, `.gitattributes`, `.gitignore`, `.nvmrc`
- `.sembleignore`
- `scheduled/**` (cron job YAML templates — but if user customized one, surface it)
- `package.json`, `bun.lock`, `pyproject.toml`, `requirements.txt`
- `LICENSE`

### PERSONALIZED — files with `[CUSTOMIZE]` markers or user-edited config

These files have structured structure that upstream maintains, but contain `[CUSTOMIZE]` sections where the user adds their own content. The agent should **propose** a merge, not auto-take upstream.

- `AGENTS.md` — has `[CUSTOMIZE]` markers for issue tracker, remote access
- `README.md` — has `[CUSTOMIZE]` markers in some sections
- `.opencode/opencode.json` — user may have trimmed MCP servers via setup
- `work/README.md` — user adds their repos here
- `spaces/README.md` — user adds their spaces here
- `memory/README.md` (if user customized stubs)
- `artifacts/README.md`

### USER-OWNED — user creates all content, upstream should never touch

These directories contain personal content. Upstream changes here indicate either a template update (acceptable) or a mistake (flag it).

- `wiki/**`
- `memory/sessions/**`, `memory/staging/**`, `memory/reviews/**`
- `spaces/<name>/**` (specific user spaces, not the template)
- `artifacts/**` (except README.md and _TEMPLATE.md)
- `work/<repo>/**` (sub-repos)

## Auto-merge SAFE files

For each SAFE file that has upstream changes:

```bash
git checkout upstream/main -- <file>
git add <file>
```

If the file was deleted upstream, remove it locally:

```bash
git rm <file>
```

Track which files were auto-merged and report them at the end.

**Edge case — user-local changes to SAFE files:** Check `git diff HEAD -- <file>` before checking out upstream. If the user has local modifications, **do not auto-overwrite** — move it to the PERSONALIZED list and ask the user.

## Smart-merge PERSONALIZED files

For each PERSONALIZED file:

### 1. Read both versions

```bash
git show upstream/main:<file> > /tmp/upstream-version
cat <file>  # current version
```

### 2. Identify the merge structure

For files with `[CUSTOMIZE]` markers (AGENTS.md, README.md sections):

- The user's content lives between `<!-- [CUSTOMIZE] ... -->` markers
- Upstream changes outside those markers should be taken
- User content inside those markers should be preserved
- If upstream **added a new `[CUSTOMIZE]` section**, include it
- If upstream **removed or moved a `[CUSTOMIZE]` section**, surface it to the user — don't silently drop their content

### 3. Propose a merged version

Construct the merged file in `/tmp/<file>-merged`. Use your judgment:

- Take upstream's structural changes (new sections, bug fixes, rewording)
- Preserve user's content inside `[CUSTOMIZE]` blocks
- If upstream and user both changed the same non-marked section, prefer upstream (structural) but note the conflict

For `opencode.json`: preserve the user's MCP server set (they may have trimmed during setup). Only add new MCP servers that upstream added; never remove servers the user kept. If upstream **removed** an MCP server, surface it — ask before removing.

### 4. Show the user the diff

```bash
diff <file> /tmp/<file>-merged
```

Present this clearly. Then ask, **per file**:

```
AGENTS.md has upstream changes. I've proposed a merge that preserves
your [CUSTOMIZE] sections. Options:
  1. Use my proposed merge (recommended)
  2. Take upstream version (discard your changes)
  3. Keep your version (skip upstream changes)
  4. Show me the raw diff
```

Wait for the user's choice per file. Apply it: copy the chosen version to the actual file path and `git add` it.

If the user chose "Show me the raw diff", print `diff <file> <(git show upstream/main:<file>)` and re-ask.

## USER-OWNED files

For files in `wiki/`, `memory/sessions/`, `spaces/<name>/`, `artifacts/` (except README.md and `_TEMPLATE.md`):

If upstream changed any of these, **stop and surface to the user**. This shouldn't happen in normal operation. Possible causes:
- Template update added a new stub to `wiki/` or `memory/` — show user, ask if they want it
- Mistake (upstream accidentally committed personal content) — flag it, don't apply

## New files (added upstream)

If upstream added a new file in a SAFE directory (e.g., new skill, new script), just take it:

```bash
git checkout upstream/main -- <new-file>
git add <new-file>
```

If upstream added a new file in a USER-OWNED directory, surface it to the user and ask.

## Verify the merge

After all files are staged:

### 1. Dependencies check

If upstream changed `package.json`, `.opencode/package.json`, or `requirements.txt`:

```bash
bun install --silent
(cd .opencode && bun install --silent) 2>/dev/null || true
uv pip install -r requirements.txt --system -q 2>/dev/null || true
```

### 2. OpenCode version check

If upstream changed `.opencode-version`:

```bash
INSTALLED=$(opencode --version 2>/dev/null || echo "none")
EXPECTED=$(cat .opencode-version)
```

If they don't match, tell the user: "Upstream updated OpenCode to $EXPECTED. You have $INSTALLED. Run `bash scripts/setup` to install the matching version."

### 3. Smoke test

Run the same checks as `scripts/setup`:

```bash
opencode --version
headroom mcp status 2>/dev/null || echo "headroom not installed"
python3 scripts/workspace/session-index.py --help 2>/dev/null || echo "session-index broken"
bun run test 2>/dev/null || echo "tests failed"
```

If anything fails, **stop** and tell the user. Offer to abort: `git reset --hard $BACKUP_BRANCH`.

## Commit

If smoke test passed (or user chose to proceed despite warnings):

```bash
UPSTREAM_SHA=$(git rev-parse --short upstream/main)
git commit -m "Sync with upstream ($UPSTREAM_SHA)

Auto-merged: <list of SAFE files>
Smart-merged: <list of PERSONALIZED files with user choices>
Skipped: <list of USER-OWNED files if any>

Backup branch: $BACKUP_BRANCH"
```

## Report

After committing, print a clear summary:

```
✓ Synced with upstream (abc1234)

Auto-merged (safe files):
  scripts/setup
  .opencode/skills/agent/sync-upstream/SKILL.md
  ...

Smart-merged (personalized):
  AGENTS.md — preserved your [CUSTOMIZE] sections
  .opencode/opencode.json — kept your trimmed MCP servers

New files added:
  .opencode/skills/engineering/new-skill/SKILL.md

Skipped (user-owned, no upstream changes):
  wiki/, memory/sessions/, spaces/myspace/

Smoke test: all passed

Backup: git reset --hard $BACKUP_BRANCH if anything looks wrong
```

## Failure modes

### Merge went wrong mid-way

If something fails and you've already staged some changes:

1. Tell the user what failed
2. Offer to abort: `git reset --hard $BACKUP_BRANCH` (discards all staged changes)
3. Or offer to commit what's been merged so far and let them clean up manually

### User cancels

If the user says "stop", "cancel", or "abort" at any point:

```bash
git reset --hard $BACKUP_BRANCH
git checkout main  # or whatever branch they were on
```

Tell them: "Aborted. Nothing was changed. Backup branch is still there if you want to inspect."

### Upstream has diverged significantly

If `git diff HEAD..upstream/main --stat | tail -1` shows more than ~50 files changed, warn the user: "This is a large upstream sync ($N files). Consider reviewing [upstream changes](https://github.com/jamesctucker/openbench/compare/$(git rev-parse --short HEAD)...upstream/main) first. Proceed?"

For very large syncs, suggest doing it file-by-file across multiple sessions.

## Notes

- This skill reads files but does not run any destructive git operations without explicit user approval (except `git checkout upstream/main -- <safe-file>` for SAFE files, which is documented as auto-take behavior)
- The backup branch is never deleted by this skill — the user can clean up old backups with `git branch -D backup-pre-sync-*` later
- If the user has committed uncommitted local changes between syncs, those are preserved in the backup branch
- Merges happen on the user's current branch, not a feature branch — this matches the "personal repo" mental model where the user works directly on `main`
