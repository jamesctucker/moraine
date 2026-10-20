---
name: review-memory
description: Analyze recent session summaries to identify repeated workflows, manual patterns, and automation opportunities. Use when user wants to review sessions, find patterns, or improve the agent ecosystem. For finding a specific past discussion use session-search; for staging cleanup use memory-promoter.
---

# Memory Review

## When to use

User says "review my sessions", "analyze memory", "find patterns", "what can be automated", or periodically when enough sessions have accumulated.

This skill works across sessions. For one session that ran long or needed repeated correction, use `retro` instead.

## Workflow

### 1. Scan sessions

Read session summaries from `memory/sessions/`. Look at the most recent chunk (e.g., last 5-10 sessions, last week, or whatever the user specifies).

### 2. Identify patterns

Look for:

| Pattern | Signals |
|---------|---------|
| **Repeated manual steps** | Same commands, same file edits, same workflows appearing across sessions |
| **Recurring questions** | User asks similar things across multiple sessions |
| **Multi-step workflows** | Sequences that span sessions but lack a structured guide |
| **Untracked context** | Information the agent had to re-discover or ask the user for each session |
| **Tool gaps** | Operations that required awkward workarounds or multiple tool calls |

### 3. Write findings

Create `memory/reviews/<YYYY-MM-DD>.md`:

```md
# Memory Review: <date range>

## Candidates for skills

<Patterns that could become their own .opencode/skills/<name>/SKILL.md.>
Each: what the skill would do, trigger phrases, source session.

## Candidates for commands

<Patterns that suit a slash-command or alias.>

## Candidates for plugins

<Patterns complex enough to need a plugin.>

## Memory gaps

<Information that future sessions will need and should be persisted to memory/index.md.>

## Index update suggestions

<Proposed additions to memory/index.md based on this review.>
```

### 4. Offer to act

After presenting findings, ask the user which candidates they want to build. Use `create-skill` for skill candidates, or scaffold commands/plugins as appropriate.

## Rules

- Focus on actionable patterns, not just descriptive summaries.
- Reference specific session files for each finding.
- Rank candidates by impact (how many sessions would benefit).
