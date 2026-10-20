# Your first session

**Definition of done:** in a second session, the agent recalls what you did in the first without being told. If it can, the workspace is working. If it can't, the troubleshooting section at the bottom tells you which link broke.

Budget: 20 minutes. You need a working install (`bash scripts/setup`) and a model provider (`opencode auth list` shows something).

## 1. Scaffold a project (5 min)

Start OpenCode in the repo root:

```bash
opencode
```

Then:

> Scaffold a project called Checkout — a small web service I'm building to learn this workspace.

The `scaffold-project` skill interviews you briefly, then creates the top note and adds it to the index. Answer in one line per question; you can fill in detail later.

**Expect:**

- `wiki/1 Projects/Active/Checkout/00 Top Note.md` with `status`, `priority`, and `next-action` frontmatter
- a new row in `wiki/1 Projects/projects.md`

If the file lands somewhere else, stop and fix it now — every later session reads this structure.

## 2. Do one small piece of real work (10 min)

Keep it small enough to finish:

> Read the Checkout project note, then add a health endpoint with a test.

The agent reads the project note, writes the code, runs the test, and commits. Steer as it goes — correcting the agent mid-run is the normal mode, not a failure. The point is to produce something a session summary can describe.

**Expect:** a commit in the project repo, and tests passing.

## 3. Wrap up (2 min)

> Wrap up this session.

The `session-handoff` skill writes `memory/sessions/<date>-<slug>.md` and updates `memory/index.md`.

**Expect:**

- a new file in `memory/sessions/`
- the project under **Active projects** in `memory/index.md`
- any real decision under **Recent decisions**

Review the summary before you move on. It is what the next session will believe.

## 4. Prove recall (3 min)

Start a new session and ask:

> What did I work on yesterday, and what's the next step?

The agent reads `memory/index.md`, follows the link to the session summary, and answers. **That's the aha moment.** No re-explaining, no pasting context.

## If recall fails

Check the chain in order — it only takes one missing link:

1. **Did the summary get written?** `ls memory/sessions/` for today's file.
2. **Is it indexed?** `memory/index.md` should list the project and, if relevant, the decision.
3. **Is the project linked?** The top note should be reachable from `wiki/1 Projects/projects.md`.
4. **Are the links intact?** Run `.venv/bin/python scripts/workspace/validate.py` — it flags broken wikilinks and index gaps.

## What good looks like after a week

- `memory/index.md` stays short — active projects, live threads, recent decisions. It is an index, not a journal.
- Session summaries name decisions and next actions, not a play-by-play.
- Each project has one top note; detail lives in its own notes beneath it.
- After a handful of sessions, run `review-memory` to find repeated work worth turning into a skill, and `retro` after any session that ran long or needed repeated correction.

## Where things go

If you're unsure whether a note belongs in `memory/`, `wiki/`, or `artifacts/`, see [The four stores](../README.md#the-four-stores) — short version: the agent writes `memory/` and `artifacts/`, you write `wiki/`.
