# Notice

Impeccable
Copyright 2025-2026 Paul Bakaus

## Anthropic frontend-design Skill

The `impeccable` skill in this project builds on Anthropic's original frontend-design skill.

**Original work:** https://github.com/anthropics/skills/tree/main/skills/frontend-design
**Original license:** Apache License 2.0
**Copyright:** 2025 Anthropic, PBC

This project extends the original with:
- 7 domain-specific reference files (typography, color-and-contrast, spatial-design, motion-design, interaction-design, responsive-design, ux-writing)
- 23 commands
- Expanded patterns and anti-patterns

## Typecraft Guide Skill

The `typography.md` reference in this project incorporates a set of tactical additions merged in from ehmo's `typecraft-guide-skill` at the author's request: dark-mode weight/tracking compensation, `font-display: optional` vs `swap`, preload-critical-weight-only guidance, variable fonts for 3+ weights, `clamp()` max-to-min ratio bound, responsive measure/container coupling, `text-wrap: balance` / `pretty`, `font-optical-sizing: auto`, ALL-CAPS tracking quantification, and the paragraph-rhythm rule (space OR indent, never both).

**Original work:** https://github.com/ehmo/typecraft-guide-skill
**Original license:** MIT; see `reference/typecraft-guide-skill.LICENSE.txt`
**Author:** ehmo

## Embedded modern-screenshot build

`scripts/modern-screenshot.umd.js` is the vendored UMD build of `modern-screenshot` 4.7.0.

**Original work:** https://github.com/qq15725/modern-screenshot
**Original license:** MIT; see `scripts/modern-screenshot.LICENSE.txt`
**Copyright:** 2021-present wxm

## Moraine distribution changes

Moraine distributes Impeccable v3.1.1 with local adaptations: category-aware skill and script paths, harness-discovery pinning changes, workspace-integration guidance, and setup/shared-design material extracted from `SKILL.md` into reference files. Personal names and paths were genericized for the public template. These changes are also recorded in `THIRD_PARTY_NOTICES.md` at the repository root.
