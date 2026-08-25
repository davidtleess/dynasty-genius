# Dynasty Genius: Build the Product

Dynasty Genius is a decision-support product for David's Superflex PPR dynasty league. Agents on
this repository are product builders: understand the problem, design the solution, implement it,
and prove that it works.

# ⛔ PARALLEL WORK PROTOCOL — read before you touch anything

Multiple agents work this repo at the same time. These rules exist so you cannot destroy someone
else's work by accident. They are mechanical, not procedural: follow them and collisions become
impossible rather than merely forbidden.

## 1. Never work in the shared trunk

`~/dynasty-genius-product` is shared. Do not edit files there, do not commit there, do not run
experiments there.

```bash
~/dg-build/bin/dg-work.sh DG-014        # your own worktree + branch, correctly linked
```

One ticket → one worktree → one branch (`ticket/DG-NNN`). When you are done, `dg-land.sh` merges it
and removes the worktree.

## 2. Claim your ticket before you start

Open `~/dg-build/tickets/DG-NNN-*.md` and put your session name in the `Lane:` field. If a lane is
already there, pick a different ticket. First writer wins; there is no arbitration.

## 3. Never `git add -A`, `git add .`, or `git commit -a`

The trunk carries dozens of uncommitted files that are not yours. Add explicit paths only:

```bash
git add src/dynasty_genius/models/engine_b_contract.py    # yes
git add -A                                                # never
```

## 4. The heavy data is shared and READ-ONLY

`app/data` is 15 GB and `.venv` is 2.3 GB. `dg-work.sh` symlinks them so your worktree is instant
instead of a 17 GB copy. **A symlink means you are reading the real thing.** Do not write to,
migrate, vacuum, or delete anything under a symlinked path.

If your ticket genuinely needs to write to a shared store, say so:

```bash
~/dg-build/bin/dg-work.sh DG-020 --writable app/data/fc_snapshots.db   # copies that one store
```

## 5. Write outputs run-scoped. Never in place.

New artifacts go to `runs/<UTC timestamp>/`. Never overwrite an existing run directory, model
artifact, or report — even yours, even if it looks wrong.

*A 23-round run record was overwritten with no backup on 2026-08-17. That is the rule's origin.*

## 6. Do not touch `.venv`

It is shared and symlinked. No `pip install`, no upgrades, no `requirements.txt` edits without a
ticket. A dependency change breaks every session running at that moment.

## 7. Stay out of the 09:00–10:15 ET window

Ten launchd jobs write to `app/data` in that window. Do not hand-run a scheduled producer while it
is scheduled to fire, and do not assume a file is stable if you read it then.

## 8. Land one at a time

```bash
~/dg-build/bin/dg-land.sh DG-014
```

It rebases on trunk, runs the tests, merges, pushes and removes the worktree — and refuses if the
tests fail or someone else is mid-merge. Do not merge by hand.

## 9. ⛔ Studio's directory is off limits

No agent reads, lists, writes, copies, backs up or inspects anything in `~/frontend-studio`.
If a task appears to require it, the task is wrong. Stop.

## 10. Say the command you ran

Every claim about the repo carries the command that produced it or the `file:line` you read. Your own
earlier statement is not a source — re-run it. A close that says "done" is worth less than one that
pastes the output.

---

**If two of these ever conflict, take the one that touches less.**

---


You are an AI agent working on Dynasty Genius, a machine-learning asset management system for David's Superflex PPR league.

## What good work looks like

- Own outcomes end to end. Investigate the real product, data, and code before choosing a fix.
- Solve root causes and simplify the system. Prefer working product code and user-visible value over
  coordination machinery, status artifacts, or process documents.
- Make reasonable product and technical decisions autonomously. Ask David only when a choice changes
  the product direction, creates material risk, spends money, or requires access he has not granted.
- Keep scope coherent. Fix adjacent breakage required by the solution; leave unrelated changes alone.
- Test behavior in proportion to risk. For UI work, exercise the actual rendered surface—not only
  component tests. For data/model work, verify lineage, replayability, and failure behavior.
- Finish with a concise handoff: outcome, important decisions, tests run, and any remaining risk.

## Product truth

- `PRODUCT.md` defines the experience and product intent. `DESIGN.md` defines the visual system.
- Model output and market opinion are different signals. Keep market values out of model features
  and present disagreement honestly.
- Never fabricate certainty, evidence, freshness, or successful data. Missing or stale inputs must be
  visible and fail closed where they could produce a misleading decision.
- Preserve source provenance, identity resolution, point-in-time integrity, deterministic replay, and
  reproducible model artifacts.
- Do not hardcode aging cliffs or turn athletic testing into a mechanical score boost without
  validated backtesting.
- Do not turn an unvalidated hypothesis into product truth. In particular, QB rushing remains a
  registered hypothesis under test until the study is completed and its result is accepted.
- User-facing language should help make a fantasy-football decision; do not expose internal pipeline
  or governance vocabulary as product copy.

## Engineering boundaries

- Work in an isolated branch/worktree and preserve other people's changes.
- Never mutate shared data or environments as a side effect of testing.
- Do not overwrite versioned model, capture, or report artifacts. Produce run-scoped outputs.
- Keep secrets and paid-provider data out of git.
- Use ordinary code review, tests, linting, and real-surface QA. There are no mandatory agent ledgers,
  cockpit rounds, governance reads, ritual status files, or inter-agent messaging protocols.
