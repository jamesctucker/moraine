---
name: research
description: Research a question against primary sources and persist the findings as Markdown — into the owning wiki project folder, or as a numbered artifact when no project owns it. Use when the user asks to research a topic, gather docs or API facts, verify claims against sources, or delegate reading legwork to a background agent.
---

# Research

The deliverable is a **file**, not a chat answer. Delegate the reading to a background subagent so the main thread stays free, then report the path and the strongest findings.

## 1. Pick the persistence path

Decide this before delegating — the subagent needs the exact output path.

**Path A — a project owns the question.** If the topic maps to a project folder under `wiki/1 Projects/` (any status, including nested folders like `Active/AI Experiments/<Project>/`):

- Write into that project folder.
- Take the next free numeric prefix in the folder (`00 Top Note.md` is reserved): `NN <Title>.md`.
- Add a `[[NN <Title>]]` wikilink to the project's `00 Top Note.md` under `## Links` (or the closest equivalent section).
- Do not consume an artifact number.

**Path B — no project owns it.** Otherwise create an artifact:

```bash
python scripts/workspace/next-artifact.py --claim <slug> --title "<Title>" --context "<one line on why this exists>"
```

- Never hand-pick the number; `--claim` allocates it exclusively.
- Keep the template's header block and Table of Contents with anchor links.
- Put the research body under the TOC.

If two projects plausibly own the question, ask one question before writing. Do not duplicate the file into both.

## 2. Delegate the reading

Call `subagent` with:

- `agent`: `general`
- `background`: `true`
- `description`: a short label for the question
- `prompt`: the question, the exact output path, the source rules below, and the file shape below

Tell the user the path and the questions being checked as soon as the subagent is dispatched. When it finishes, verify the file exists and carries citations, then report 3–5 key findings plus the path — and ask the user for their one-paragraph synthesis for the `## My synthesis` section (they dictate, you insert verbatim). The file may be delivered with that section blank, but the research is not done until the user has written it in their own words; the reading legwork is delegable, the synthesis is not.

Skip the file and the subagent for a single fact that one page or one API signature answers — answer inline, cite the source, and offer to persist it. Persist whenever the user asks for research, a write-up, or a survey of multiple sources.

If the subagent fails or returns unverified claims, finish the research inline rather than reporting an empty file.

## 3. Source rules

1. **Primary sources only**: official documentation, source code, specs, RFCs, first-party APIs, changelogs, standards bodies.
2. Follow every claim back to the source that owns it. Never cite a blog post or summary describing the primary source.
3. Use Context7 for library and framework docs; `webfetch` for raw docs, GitHub files, and API references; `websearch` to *locate* the primary source, not to replace it.
4. If primary sources conflict, state both and cite both.
5. If a primary source is unreachable, mark the claim unverified. Do not fill the gap with a secondary write-up.
6. Prefer the project's own code and `work/` repos over external docs when the question is about this workspace.

## 4. File shape

```markdown
# <Title>

> **Date:** YYYY-MM-DD
> **Question:** <the question in one line>
> **Status:** answered | partial

## Answer

<1–3 sentences.>

## My synthesis

<Leave blank. The user writes one paragraph in their own words after delivery — the research is not done until this is filled.>

## Findings

<Grouped by sub-question. Inline citations [1], [2] immediately after each claim.>

## Open questions

<What could not be verified, and what would settle it.>

## Sources

[1] Title — URL
[2] Title — URL
```

Path A files carry no YAML frontmatter (matching existing project research notes): use the header block, sections, and Sources list as written. For Path B, the artifact template supplies the header and TOC; this shape is the body.

## Done when

- Every claim in the file cites a primary source.
- The path is reported to the user.
- Path A links the new file from `00 Top Note.md`; Path B reports the claimed artifact number.
- Gaps are listed under Open questions rather than smoothed over.
- `## My synthesis` holds the user's own paragraph (delivered blank, filled by them — prompt for it in the findings report).
