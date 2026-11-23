# packs/local

Your pack. It is always enabled, is never listed in `moraine.yaml`, and upstream sync never writes here.

| Path | What goes there |
|------|-----------------|
| `skills/<id>/SKILL.md` | Skills you write. `moraine sync` links each folder into `.agents/skills/`. |
| `AGENTS.md` | Conventions you want every session to read. Read at session start, right after `memory/index.md`. |
| `docs/` | Shared documents your skills or sessions refer to. |
| `jobs/<name>.yaml` | Your own scheduled jobs. Installed only while the `automation` pack is enabled. |

Create directories as you need them. To add a skill, ask the agent to use `create-skill`, or copy a skill folder here whole and run:

```bash
python3 scripts/moraine sync
```

A skill ID that already exists in core or in an enabled pack is a collision; sync stops and names both folders. Rename yours.
