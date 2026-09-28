---
name: plan-hardening
description: Hardening review for a plan document — find risks, gaps, and edge cases; add agent-execution safety; split at concern boundaries; produce pre-flight checks. Use when the user wants to review, harden, stress-test, or split a plan ("review this plan", "harden the migration plan", "find gaps in this spec", "split this doc").
---

# Plan Hardening

Systematic review of a plan document to surface risks, gaps, and structural improvements. Born from the AWS-to-Hetzner migration hardening sessions (2 passes) and the session-search plan review. Not a rewrite — a structured stress test.

## When to use

- User says "review this plan", "harden this", "find gaps", "stress-test this"
- A plan document is complete but hasn't been challenged for edge cases
- A large plan doc needs splitting at concern boundaries
- Agent-assisted execution is in scope and needs safety rules
- Before handing a plan to an agent for execution

## Workflow

### Phase 1 — Read the plan

Read the full plan document. Note:
- What it claims to do (scope)
- What it explicitly excludes (out-of-scope)
- What it assumes (prerequisites, existing infra, user knowledge)
- Its current structure (single file? multiple? cross-references?)

### Phase 2 — Risk register

Produce a risk table. For each risk:

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| ... | Low/Med/High | Low/Med/High | Concrete action in the plan |

Focus on:
- **Data loss**: destructive operations, migration steps, schema changes
- **State drift**: steps that span sessions, env confusion (staging vs prod)
- **Dependency surprises**: version mismatches, missing features, API deprecations
- **Hallucination surface**: names the agent might invent (resource IDs, IPs, region labels)
- **Silent failures**: steps where success isn't verifiable by a command's exit code
- **Rollback gaps**: what happens if step N fails partway through

### Phase 3 — Agent-execution safety (if applicable)

If an agent will execute any part of the plan, add or check for:

1. **Confirmation gates**: destructive commands require `"yes, delete <exact-resource-name>"`
2. **Env vars, never literals**: credentials referenced via `$VAR`, not inlined
3. **Phase marker files**: `/opt/<project>/PHASE-N-VERIFIED` to prevent re-running destructive steps on resume
4. **Staging-then-production hard gate**: staging must pass 100% verification before touching production
5. **Pre-flight checks**: before each critical step, verify the target environment (hostname, IP, DB URL)
6. **Verification-by-default format**: every step ends with a verification command, not "check if it worked"
7. **Audit log**: every command run and its output saved to a timestamped file
8. **Session start checklist**: what a fresh agent session must ask before doing anything

See `artifacts/06a-agent-execution-safety.md` for the canonical example.

### Phase 4 — Doc structure evaluation

Ask whether the document is at the right concern boundary:

- **Single concern per file**. A runbook + safety policy + cleanup instructions are three concerns.
- **Audience clarity**: who reads this file and when? An execution-time reader needs different info than a reviewer.
- **Cross-reference fragility**: splitting by milestone creates fragile links between docs that drift independently. Prefer splitting by concern (runbook / policy / cleanup), not by phase.

If the doc benefits from splitting, propose where the seams are and what each file contains. Update cross-references so each file stands alone with a "See Also" section.

### Phase 5 — Pre-flight checklist

Produce a concrete checklist of things to verify *before* execution begins. These are verification commands, not reminders. Examples:

```markdown
- [ ] `df -h /` — confirm ≥20GB free on target
- [ ] `psql "$STAGING_DATABASE_URL" -c "SELECT pg_size_pretty(pg_database_size(current_database()));"`
- [ ] `aws s3 ls s3://<bucket> --summarize | grep "Total Size"`
- [ ] `dig +short <domain>` — confirm current DNS TTL
```

### Phase 6 — Write findings

Structure findings as:

```markdown
## Risks found
<risk register table>

## Safety gaps
<missing gates, env var issues, missing verification steps>

## Structural recommendations
<doc split proposal, cross-reference fixes>

## Pre-flight checklist
<numbered verification items>
```

Add findings directly to the plan document as new sections, or produce a companion doc if the plan is already large (>500 lines). For companion docs, use the naming convention `<plan-base-name>a-<concern>.md` (e.g., `06a-agent-execution-safety.md`).

## Rules

- **Find risks, don't rewrite prose.** The plan's voice and structure are the author's; your job is to find what's missing.
- **Be specific.** Not "add error handling" but "`pg_restore` can fail silently with exit code 0 — add `-v` and grep for 'ERROR' in output."
- **Every verification must be a command.** Not "confirm DNS propagated" but `dig +short <domain> @8.8.8.8`.
- **Agent safety applies to any agent-executed phase**, not just destructive ones. Non-destructive steps can also cause state drift.
- **Don't duplicate the plan.** If the plan already covers a risk well, acknowledge it and move on.

## Reference

Canonical examples in this workspace:
- `artifacts/06-aws-to-hetzner-migration.md` — runbook after hardening
- `artifacts/06a-agent-execution-safety.md` — extracted safety policy
- `artifacts/06b-post-migration-tasks.md` — extracted cleanup doc
- `wiki/1 Projects/The Garage/plan-session-search-semble.md` — reviewed plan
