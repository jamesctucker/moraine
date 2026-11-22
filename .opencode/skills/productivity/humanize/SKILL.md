---
name: humanize
description: Remove AI writing patterns and restore natural human voice. Use when user says "humanize this", "de-AI this", "make this sound more human", or pastes text that sounds AI-generated.
license: CC-BY-SA-4.0. See NOTICE.md for Wikipedia attribution and share-alike terms.
---

# Humanize

Remove AI writing patterns and restore natural human voice. Based on [Wikipedia's Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing).

## Task

1. Scan the input for AI patterns (see [PATTERNS.md](./PATTERNS.md) for the full catalog)
2. Rewrite problematic sections with natural alternatives
3. Preserve the core message and intended tone (formal, casual, technical, etc.)
4. Inject actual personality — don't just remove bad patterns, see **Adding soul** below
5. Do a final anti-AI pass: ask "what still makes this obviously AI-generated?", answer briefly, then revise once more

## Voice calibration (optional)

If the user provides a writing sample, analyze it before rewriting:

- Note sentence length patterns, word choice level, how they start paragraphs, punctuation habits, verbal tics, how they handle transitions
- Match those patterns in the rewrite — don't just strip AI patterns, replace them with *their* patterns
- If they write short sentences, don't produce long ones. If they use "stuff", don't upgrade to "components."

**How to provide a sample:**
- Inline: "Humanize this. Here's a sample of my writing: [sample]"
- File: "Humanize this. Use my writing style from [path] as a reference."

When no sample is provided, fall back to the default: natural, varied, opinionated voice.

## Adding soul

Removing patterns is only half the job. Sterile writing is just clean slop.

- **Have opinions.** React to facts, don't just report them. "I genuinely don't know how to feel about this" beats a neutral list.
- **Vary rhythm.** Short punchy sentences. Then longer ones that take their time getting somewhere. Mix it up.
- **Acknowledge complexity.** "This is impressive but also kind of unsettling" beats "This is impressive."
- **Use "I" when it fits.** First person is honest, not unprofessional.
- **Be specific about feelings.** Not "this is concerning" but "there's something unsettling about agents running at 3am while nobody's watching."
- **Let some mess in.** Tangents, asides, and half-formed thoughts are human. Perfect structure is algorithmic.

## Process

1. Read the input carefully
2. Identify all pattern instances (see [PATTERNS.md](./PATTERNS.md))
3. Rewrite each problematic section
4. Ensure the result sounds natural when read aloud, varies structure, uses specific details, avoids simple-is/are/has substitutions
5. Write the **draft rewrite**
6. Ask: "What still makes this obviously AI-generated?" — answer briefly
7. Revise once more to remove those tells
8. Write the **final rewrite**

## Output format

1. **Draft rewrite**
2. **Anti-AI pass** — brief bullets on remaining tells
3. **Final rewrite**
4. Brief summary of changes (optional, include when helpful)

## Hard cases

**Input is mostly filler.** Strip the patterns and the honest version will be dramatically shorter — maybe a third, maybe a tenth. Don't pad it back out. Flag this in the changes summary: "The original was mostly filler — the humanized version is significantly shorter on purpose."

**Input contains suspicious facts.** LLM text often contains plausible-sounding details that are made up: invented geography, fabricated study citations, named anonymous sources. Drop them rather than carry them forward. Note any removals in the changes summary. Better to be shorter and more cautious than to launder hallucinations into cleaner prose.

## Patterns reference

All 29 patterns with before/after examples: [PATTERNS.md](./PATTERNS.md)

Quick index:
- **Content (1–6):** significance inflation, notability emphasis, -ing phrases, promotional language, weasel words, formulaic challenges sections
- **Language (7–13):** AI vocabulary, copula avoidance, negative parallelisms, rule of three, synonym cycling, false ranges, passive/subjectless fragments
- **Style (14–19):** em dash overuse, boldface overuse, inline-header lists, title case headings, emojis, curly quotes
- **Communication (20–22):** chatbot artifacts, knowledge-cutoff disclaimers, sycophantic tone
- **Filler (23–29):** filler phrases, excessive hedging, generic conclusions, hyphenated word pairs, persuasive authority tropes, signposting, fragmented headers
