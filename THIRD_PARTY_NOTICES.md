# Third-Party Notices

Moraine's root [MIT license](LICENSE) covers Moraine's original engineering. It does not relicense the bundled components listed below. Each component retains its upstream license, and each bundled skill carries a local copy of that license so it can also be copied on its own.

## Impeccable

| Component | Bundled path | Upstream and version | License |
|---|---|---|---|
| Impeccable | `.opencode/skills/design/impeccable/` | [pbakaus/impeccable@`4af581e`](https://github.com/pbakaus/impeccable/tree/4af581e23f17d112d8f9d6b7a5b7ff37823494e1), skill v3.1.1 | Apache 2.0 — `LICENSE`; upstream attribution and Moraine changes in `NOTICE.md` |
| Anthropic frontend-design skill | Incorporated into Impeccable | [anthropics/skills](https://github.com/anthropics/skills/tree/main/skills/frontend-design), as attributed by Impeccable v3.1.1 | Apache 2.0 — attributed in Impeccable's `NOTICE.md` |
| Typecraft Guide Skill | Incorporated into `reference/typography.md` | [ehmo/typecraft-guide-skill](https://github.com/ehmo/typecraft-guide-skill), license restored from [`8099648`](https://github.com/ehmo/typecraft-guide-skill/tree/8099648409ec73980bd693ac8d15fd3e3230072d) | MIT — `reference/typecraft-guide-skill.LICENSE.txt` |
| modern-screenshot | `scripts/modern-screenshot.umd.js` | [qq15725/modern-screenshot](https://github.com/qq15725/modern-screenshot), npm 4.7.0 (the version locked by Impeccable v3.1.1) | MIT — `scripts/modern-screenshot.LICENSE.txt` |

Moraine's Impeccable adaptations add category-aware paths, harness-discovery pinning changes, workspace guidance, and local setup/shared-design reference material; they also genericize personal names and paths. The bundled upstream notice and local change notice are both in `.opencode/skills/design/impeccable/NOTICE.md`.

## Matt Pocock skills

The following components derive from [mattpocock/skills](https://github.com/mattpocock/skills), licensed MIT (© 2026 Matt Pocock). Every listed skill directory contains an upstream `LICENSE` copied from the vendored-era repository, not from an unpinned latest branch.

| Bundled path | Upstream path and snapshot | Moraine changes |
|---|---|---|
| `engineering/code-review/` | `skills/engineering/code-review` @ [`3da8c01`](https://github.com/mattpocock/skills/tree/3da8c01116264675eeefbd6e9d59c734de9095cc/skills/engineering/code-review) | Two slop-check review additions; tracker-agnostic spec fallback |
| `engineering/tdd/` | `skills/engineering/tdd` @ [`3216582`](https://github.com/mattpocock/skills/tree/321658273cb1d20b76026717d027d505790106d4/skills/engineering/tdd) | Shared GLOSSARY vocabulary; shipped architecture reference |
| `engineering/diagnose/` | `skills/engineering/diagnose` @ [`7afa86d`](https://github.com/mattpocock/skills/tree/7afa86d3a5dd96edde06ffa014e16c64e733681e/skills/engineering/diagnose) | Workspace-awareness guidance and genericized paths |
| `engineering/improve-codebase-architecture/` | `skills/engineering/improve-codebase-architecture` @ [`a36584e`](https://github.com/mattpocock/skills/tree/a36584e09eaee067c425938fd66bc7ccddf089e2/skills/engineering/improve-codebase-architecture) | Workspace adaptations and genericized paths |
| `productivity/grilling/` | `skills/productivity/grilling` @ [`bc4cf90`](https://github.com/mattpocock/skills/tree/bc4cf903ff4855ce23199a8dd3bf98b3dbd7ad71/skills/productivity/grilling); companion formats derive from `skills/engineering/grill-with-docs` @ [`e7df78b`](https://github.com/mattpocock/skills/tree/e7df78bb81da39c537be810e622d2b90bbdc7dc5/skills/engineering/grill-with-docs) | Routing adaptations, merged companion formats, genericized examples, shared GLOSSARY convention |
| `engineering/domain-modeling/` | `skills/engineering/domain-modeling` @ [`d80fa0f`](https://github.com/mattpocock/skills/tree/d80fa0f4ebe0c5714af0adf8670336065233ecc6/skills/engineering/domain-modeling) | Description and OpenCode metadata adaptations; plain-text example paths |
| `engineering/wayfinder/` | `skills/engineering/wayfinder` @ [`8295b8e`](https://github.com/mattpocock/skills/tree/8295b8e10d4cdb6cce772a56dda7b7c37075074d/skills/engineering/wayfinder) | Local tracker setup pointer; placeholder example cleanup |
| `engineering/wizard/` | `skills/engineering/wizard` @ [`49dd158`](https://github.com/mattpocock/skills/tree/49dd158d1076134a641b33efb035946536778336/skills/engineering/wizard) | None |
| `engineering/prototype/` | `skills/engineering/prototype` @ [`3216582`](https://github.com/mattpocock/skills/tree/321658273cb1d20b76026717d027d505790106d4/skills/engineering/prototype) | None |
| `productivity/to-questionnaire/` | `skills/productivity/to-questionnaire` @ [`3216582`](https://github.com/mattpocock/skills/tree/321658273cb1d20b76026717d027d505790106d4/skills/productivity/to-questionnaire) | Description/trigger adaptations; `disable-model-invocation` dropped |
| `productivity/teach/` | `skills/productivity/teach` @ [`ad5400b`](https://github.com/mattpocock/skills/tree/ad5400b930b297b0c0cb231ff1ffe42a7da666aa/skills/productivity/teach) | Description, learning-workspace paths, lesson caps, genericized examples |
| `agent/retro/` | `skills/engineering/retro` @ [`a7d038f`](https://github.com/mattpocock/skills/tree/a7d038f6bf7f01b516408e95e2fb56e0b338fa6f/skills/engineering/retro) | Adapted for single-session reviews, evidence gates, and mechanical fixes |

## Obra Superpowers skills

These components derive from [obra/superpowers](https://github.com/obra/superpowers), licensed MIT (© 2025 Jesse Vincent). Each listed skill directory contains the upstream `LICENSE`.

| Bundled path | Upstream path and snapshot | Moraine changes |
|---|---|---|
| `productivity/brainstorming/` | `skills/brainstorming` @ [`b36e082`](https://github.com/obra/superpowers/tree/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/brainstorming) | Narrowed trigger description; numbered artifact conventions |
| `engineering/writing-plans/` | `skills/writing-plans` @ [`b36e082`](https://github.com/obra/superpowers/tree/b36e0829c6d0140e93cfef2ca599b1b07d4a7797/skills/writing-plans) | Added Program Design guidance; Moraine artifact and execution conventions |
| `engineering/executing-plans/` | `skills/executing-plans` @ [`09fc6e0`](https://github.com/obra/superpowers/tree/09fc6e0f3be2a3d74e95c6058408a76972e4571b/skills/executing-plans) | Moraine worktree, subagent, and human-review handoff conventions |

## Humanize / Wikipedia

`.opencode/skills/productivity/humanize/` adapts the pattern catalog from **Wikipedia:Signs of AI writing**, by Wikipedia contributors and WikiProject AI Cleanup.

- **Source:** [revision 1356298499, 2026-05-26](https://en.wikipedia.org/w/index.php?title=Wikipedia:Signs_of_AI_writing&oldid=1356298499)
- **License:** Creative Commons Attribution-ShareAlike 4.0 International
- **Changes:** reorganized and condensed for an OpenCode skill, with rewritten examples and editing instructions
- **Notices and complete license:** the skill's `NOTICE.md` and `LICENSE.txt`

The adapted Humanize skill is distributed under CC BY-SA 4.0. Moraine's root MIT license does not cover it.
