---
name: create-skill
description: Guide for building new agent skills with proper structure, frontmatter, and progressive disclosure. Use when user wants to create a new skill, write a SKILL.md, or set up agent capabilities.
---

# Creating Skills

Skills you write live in `packs/local/skills/<name>/SKILL.md`. Run `python3 scripts/moraine sync` afterwards to link the folder into `.agents/skills/`, where the harness discovers it.

## Name rules

Names must match `^[a-z0-9]+(-[a-z0-9]+)*$`:
- Lowercase alphanumeric, single hyphens between segments
- No leading/trailing hyphens, no consecutive `--`
- Must match the directory name exactly

## Frontmatter

```yaml
---
name: my-skill
description: What this does and when to load it. Use when [trigger phrase].
---
```

`name` and `description` are required. Optional: `license`, `compatibility`, `metadata`.

## Writing the description

The description is what agents see when deciding which skill to load. Make it count:

- **First sentence**: what the skill does
- **Second sentence**: "Use when [context/triggers]"
- Keep it under 1024 characters
- Be specific enough that an agent can tell this skill apart from others

> Good: `Search, create, and manage notes in the Obsidian vault with wikilinks and PARA organization. Use when user wants to find, create, or organize notes in the Obsidian vault.`

> Weak: `Helps with notes.` (too vague to match on)

## Directory layout

```
my-skill/
├── SKILL.md          # Required — main instructions
├── REFERENCE.md      # Optional — extended docs
└── scripts/          # Optional — utility scripts
```

## When to split into files

Pull content out of SKILL.md when:
- SKILL.md approaches ~100 lines
- Content covers distinct sub-topics
- Advanced sections are rarely needed

Reference files from the main SKILL.md with relative links.

## When to add scripts

Add scripts when:
- The operation is deterministic (validation, parsing, formatting)
- You'd otherwise generate the same code repeatedly
- Errors need structured handling

Scripts save tokens and run more reliably than generated code.

## Process

1. **Understand the domain**: what exact task does this skill cover? What are the trigger phrases?
2. **Draft SKILL.md**: start with quick start, then workflows, then advanced references
3. **Review**: does it cover the use cases? Is anything missing or overwritten?
4. **Validate**: run `python3 scripts/moraine sync`, then `opencode debug skill` to confirm discovery

## Checklist

- [ ] Name follows the naming regex
- [ ] Directory name matches `name` in frontmatter
- [ ] `moraine sync` linked the folder into `.agents/skills/`
- [ ] Description includes a trigger phrase ("Use when...")
- [ ] SKILL.md is concise (under ~100 lines)
- [ ] No time-sensitive or hardcoded paths
- [ ] Concrete examples included
- [ ] Verified with `opencode debug skill`
