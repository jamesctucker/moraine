# Scaffold Project — Templates

All file templates and frontmatter schemas for the `scaffold-project` skill. Reference this file when scaffolding; do not invent new fields.

## Project top note

Path: `wiki/1 Projects/<Name>/00 Top Note.md`

```yaml
---
status: <idea|active|paused|backlog>
priority: <high|medium|low>
tags: [<3-5 tags from interview>]
next-action: "<verb> + <concrete deliverable> + <time-bound>"
created: <YYYY-MM-DD>
last-reviewed: <YYYY-MM-DD>
---

## Goal
<one-sentence "done" definition from interview>

## Why
<smallest version that proves the hypothesis>

## Links
- <artifact path or "TBD: spec pending">
- <related work repos / notes>

## Action Items
- [ ] <next-action from interview>
- [ ] <follow-ups surfaced in interview>

## Notes
- YYYY-MM-DD: <scaffold reason + constraints captured in interview>
```

## Area top note (single-file pattern)

Path: `wiki/2 Areas/<Name>.md`

```yaml
---
status: active
tags: [<umbrella tags>]
created: <YYYY-MM-DD>
last-reviewed: <YYYY-MM-DD>
---

# <Area Name>

<one-sentence purpose: what ongoing responsibility this area covers>

## Repos / systems

<if the area owns repos or systems, list them with stack and purpose>

## Key context

<domain-specific facts that any future agent needs to know>

## Links

- <related notes, manifests, or external docs>
```

## Area top note (directory pattern)

Path: `wiki/2 Areas/<Name>/00 Top Note.md`

Use this when the area has sub-cadences, sub-projects, or substantial content.

```yaml
---
status: active
tags: [<umbrella tags>]
created: <YYYY-MM-DD>
last-reviewed: <YYYY-MM-DD>
---

## Purpose

<one-sentence purpose: what ongoing responsibility this area covers>

## Cadences

- [[<Cadence Name>/00 Top Note|<Cadence Name>]] — <frequency>, <day/date>

## Active projects

- [[../../1 Projects/<Project Name>/00 Top Note|<Project Name>]] — <status note>

## Past projects

- <Project Name> — <one-line summary>; archived to <path>

## Notes

- YYYY-MM-DD: <scaffold reason>
```

## Cadence top note

Path: `wiki/2 Areas/<Parent Area>/<Name>/00 Top Note.md`

```yaml
---
status: active
parent-area: <parent-area-slug>
cadence: <weekly|biweekly|monthly|quarterly|on-demand>
next-cadence-day: <Monday|Tuesday|...|n/a>
tags: [<parent-area tags>, cadence]
next-action: "<next specific deliverable, e.g. '6/9 issue production and review'>"
created: <YYYY-MM-DD>
last-reviewed: <YYYY-MM-DD>
---

## Description

<one-sentence: what this cadence produces and why>

## Cadence template

<if there's a standard structure, list the sections. e.g. for a newsletter: opener, discoveries, local, send>

## Active issues / instances

- [[<current instance>]] — <status>
- <next instance name> — current focus

## Past issues / instances

See `<Past Instances>/` directory or external archive.

## Links

- [[../00 Top Note|<Parent Area>]] — parent area
- <skill or external tool references>

## Notes

- YYYY-MM-DD: <scaffold reason or migration note>
```

## Resource top note

Path: `wiki/3 Resources/<Name>.md`

```yaml
---
status: active
tags: [<topic tags>]
created: <YYYY-MM-DD>
last-reviewed: <YYYY-MM-DD>
---

## Summary

<one-sentence: what this resource is>

## Notes

- [[related-note-1]]
- [[related-note-2]]
```

## projects.md row

Path: `wiki/1 Projects/projects.md`

Add to the right section (Active / Paused / Ideas):

```markdown
| [[<Name>/00 Top Note\|<Name>]] | <status> | <priority> | <next-action> |
```

## memory/index.md updates

For projects, append under the right section:

```markdown
- **<Name>** — <one-line description>. <key context bullets>
```

For areas, under `## Areas`:

```markdown
- **[[wiki/2 Areas/<Name><.md or /00 Top Note>|<Name>]]** — <description>. Cadences: <list if any>.
```

For decision log, append under the current date:

```markdown
- **<Name> scaffolded** as <type>. <key decisions from interview>.
```

For open threads, append if there are unresolved questions or hard deadlines:

```markdown
- **<Name>**: <unresolved question or resume condition>
```

## Artifact (spec) template

Path: `artifacts/NN-<slug>.md` (use next sequential number; check existing artifacts)

```markdown
# <Title>

## Context

<Why this exists. The problem or opportunity.>

## Goals

<bulleted list of what success looks like>

## Non-Goals

<bulleted list of what is explicitly out of scope>

## Architecture

<diagram + component descriptions>

## Components

<numbered list with one-paragraph descriptions>

## Open Questions

<bulleted list of unresolved decisions>

## Build Order

<numbered list of next concrete steps>

## References

<links to related work, prior art, docs>
```

## areas.md row

Path: `wiki/2 Areas/areas.md`

```markdown
| [[<Name><.md or /00 Top Note>\|<Name>]] | <description> | <cadences, comma-separated wikilinks> |
```
