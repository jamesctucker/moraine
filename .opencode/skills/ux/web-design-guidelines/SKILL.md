---
name: web-design-guidelines
description: Review UI code for Web Interface Guidelines compliance. Use when asked to review UI, check accessibility, audit design, review UX, or check a site against best practices.
metadata:
  author: vercel (adapted)
  version: "1.0.0"
  argument-hint: <file-or-pattern>
---

# Web Interface Guidelines

> Adapted from [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills/blob/main/skills/web-design-guidelines/SKILL.md). Forked for The Garage workspace.

Review files for compliance with [Web Interface Guidelines](https://github.com/vercel-labs/web-interface-guidelines).

## How It Works

1. Fetch the latest guidelines from the source URL below
2. Read the specified files (or locate UI files in the project)
3. Check against all rules in the fetched guidelines
4. Output findings in the format specified by the guidelines

## Guidelines Source

Fetch fresh guidelines before each review:

```
https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md
```

Use WebFetch to retrieve the latest rules. The fetched content contains all the rules and output format instructions — the skill carries no hard-coded rules so it stays current with the upstream guidelines.

## Finding files

When the user provides a file or glob pattern, use that directly.

When no files are specified:

1. Check for a project in `work/<project>/` — scan for common UI directories (`src/components/`, `app/`, `pages/`, `src/`, `lib/`)
2. If no project is obvious, ask the user which files to review

## Complementary skills

- **`impeccable`** (in `design/`) — for *creating and refining* UI, not reviewing guideline compliance. Use when the review surfaces design gaps that need rebuilding. Impeccable's `audit` and `critique` commands evaluate design quality and anti-patterns; this skill evaluates guideline conformance. Both are useful; they test different things.
- **`grill-with-docs`** (in `engineering/`) — when a UX audit reveals architectural issues (e.g., component seams that leak state), switch to grilling to resolve the structural problem.

## Output

Follow the output format specified in the fetched guidelines exactly. If the guidelines specify a terse `file:line` format, use that. If they specify a different format, follow it.

After the audit, offer a brief summary: how many findings, which categories (a11y, layout, typography, etc.), and which files need the most attention.