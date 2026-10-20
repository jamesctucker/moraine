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

The `scaffold-project` skill interviews you first — 5–7 short questions, one at a time. For this sandbox project, answer along these lines:

- *What are you capturing?* "Checkout — a tiny web service I'm building to learn this workspace."
- *Finish line or deadline?* "Yes — it has a health endpoint and a passing test."
- *What does done look like?* "The health endpoint returns 200 in a test."
- *What does it replace or pause?* "Nothing — it's a sandbox project to learn the workspace."
- *Smallest version?* "The endpoint and the test, nothing else."
- *Links to existing notes or repos?* "None yet."
- *First concrete next-action?* "Add the health endpoint today."

That's the whole interview — real projects get real answers.

**Expect:**

- `wiki/1 Projects/Checkout/00 Top Note.md` with `status`, `priority`, and `next-action` frontmatter
- a new row in `wiki/1 Projects/projects.md`

If the file lands somewhere else, stop and fix it now — every later session reads this structure.

## 2. Do one small piece of real work (10 min)

Keep it small enough to finish:

> Create a small repo at work/checkout, then add a health endpoint with a test.

The agent creates the project repo, reads the project note, writes the code, runs the test, and commits. Steer as it goes — correcting the agent mid-run is the normal mode, not a failure. The point is to produce something a session summary can describe.

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

> What did I work on in my last session, and what's the next step?

(Run it the next day if you can — recall across a real gap is the honest test. Same-day works too.)

The agent reads `memory/index.md`, follows the link to the session summary, and answers. **That's the aha moment.** No re-explaining, no pasting context.

## If recall fails

Check the chain in order — it only takes one missing link:

1. **Did the summary get written?** `ls memory/sessions/` for today's file. Missing → go back to the first session and say "wrap up this session" again — the `session-handoff` skill writes it.
2. **Is it indexed?** `memory/index.md` should list the project under **Active projects**. Missing → ask the agent: "Add the Checkout project to memory/index.md" (the wrap-up normally does this).
3. **Is the project linked?** The top note should appear as a row in `wiki/1 Projects/projects.md`. Missing → ask: "Add the Checkout top note to projects.md" — or re-run step 1's scaffold.
4. **Are the links intact?** Run `.venv/bin/python scripts/workspace/validate.py` — it flags broken wikilinks and index gaps, one per line. Fix what it names, then retry step 4.

## What good looks like after a week

- `memory/index.md` stays short — active projects, live threads, recent decisions. It is an index, not a journal.
- Session summaries name decisions and next actions, not a play-by-play.
- Each project has one top note; detail lives in its own notes beneath it.
- After a handful of sessions, run `review-memory` to find repeated work worth turning into a skill, and `retro` after any session that ran long or needed repeated correction.

## Where things go

If you're unsure whether a note belongs in `memory/`, `wiki/`, or `artifacts/`, see [The four stores](../README.md#the-four-stores) — short version: the agent writes `memory/` and `artifacts/`, you write `wiki/`.
