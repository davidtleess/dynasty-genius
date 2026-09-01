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
- **One carve-out, and it is not ritual.** `docs/agent-ledger/<date>.md` is a dated FINDINGS LOG, not a
  status file: on 2026-08-31 it was the only on-disk record of several live hazards, and nothing else
  held them. Nobody must open one, write one, or round-trip through one to do work. But if you find a
  hazard that outlives your task, put it where the next person reads — this file for anything durable,
  the dated ledger for anything you want attributed and timestamped. **A finding recorded only in a
  commit message or a chat message is not recorded.**



## ⚠ LIVE AS OF 2026-09-01 — two things are broken right now

**1. The daily prediction capture has been dark since 2026-08-31 09:04, behind a green receipt.**
`model_forward_capture` aborts every run with
`required_provenance_missing: app/data/models/head_a/runs/20260524T140748Z/te_v3_metadata.json`,
while the enclosing `run_pvo_refresh` reports `status: ok`. Verify, do not assume:
```
sqlite3 "file:app/data/model_forward_capture.db?mode=ro" \
  "select capture_date,count(*) from model_forward_capture_raw group by 1 order by 1 desc limit 3"
```
2026-08-30 has 12,226 rows; **2026-08-31 has none.** The file was destroyed by a symlink accident that
morning and **is in NO backup copy** — `app/config/backup_manifest.json` names `te_v3.pkl` and
`v3_manifest.json` from that directory but never the metadata, so 14 days of offsite runs all contain
the pickle and none contains the metadata. It is not in git. It is gone. The capture reads it only to
sha256 it for provenance and **fails closed, which is correct** — do not "fix" this by making the
provenance check optional. Regenerating it breaks provenance continuity and is David's call, not yours.

**2. The trust surface describes models that no longer exist — for ALL FOUR positions.**
`app/data/backtest/model_cards/*_model_card.json` were generated **2026-05-15**; the served bundles are
`engine_b/runs/20260831T204458Z/*`. Every performance figure the product displays belongs to a model
that was replaced. This is the tight-end badge defect, four times wider, and the retrain widened it
rather than fixing it.

---

# 📍 WHERE THE PRODUCT ACTUALLY IS — updated 2026-09-01

Read this before scoping anything. It is the state, the traps, and the method — not history.
Every claim here carries the command or `file:line` that produced it, per §10.

## The one thing still broken

**COVERAGE.** `468` of `12,226` served players carry a `dynasty_value_score`; on the honest
denominator, `498` of `954` addressable players (skill position, NFL roster, active) have
**nothing**. David's roster shows three blanks. His first ruling — *"rank everyone, always;
confidence is a WIDTH, never an ABSENCE"* — is **unsatisfied**. `ENGINE_B_MIN_GAMES_T = 8`
(`src/dynasty_genius/models/engine_b_contract.py`) has never been touched.

```bash
.venv/bin/python -c "import json; d=json.load(open('app/data/valuation_runtime/universe_pvo_runtime.json')); \
print(sum(1 for r in d['players'] if (r.get('valuation') or {}).get('dynasty_value_score') is not None), 'of', len(d['players']))"
```

**The fix is a missing column, not a data gap.** `games_t` is ONE SEASON, not the player.
`ppg` has two lags, `snap_share` has one, **`games` has zero** — there is no `games_t_minus_1`
anywhere in the 39-column feature table. So the gate asks *"is this player durable?"* and is
handed exactly one season to answer with. Of the 115 players below the gate, **72 carry a
prior-season ppg in the very row being refused** and 55 carry two; only 43 are genuinely thin.
Garrett Wilson: 17 games in 2022, 17 in 2023, 7 in 2025 — and the dead-window path walks past
`ppg_t_minus_1 = 14.82` to look for a *college* prior on a four-year professional.

> ⛔ **Do NOT backfill 2024 feature rows expecting coverage to move.** The gate reads `games_t`
> off the 2025 row; a 2024 row cannot change it. 2024 is already live as `ppg_t_minus_1` for
> every player, and its absence as a ROW is the DG-029 partition, deliberate and pinned by
> `tests/contract/test_inference_partition_seasons.py`. That scope is plausible, expensive,
> and moves coverage by zero.

## What changed underneath you

**Served value is now a hurdle.** `dynasty_value_score` = `P(plays) × E[points | plays]`
(`ee57d802`, `apply_availability` in `pvo_assembler.py`). The availability model is
`src/dynasty_genius/models/availability.py` — walk-forward pooled AUC 0.811.

> ⚠ The live age effect moved −0.2593 → −0.4028 against a market of −0.3855. **That is
> ALIGNMENT WITH THE MARKET, NOT PROOF OF PROFIT.** It means the model stopped disagreeing
> with the market for a reason we knew was wrong. **Nothing in this product has ever graded a
> prediction against a real football outcome.** Do not quote that number as an edge.

> ⚠ **Known simplification:** `score_rows` fits at SCORING TIME from
> `app/data/training/engine_b_features_v2.csv`, so regenerating that CSV changes served values
> with **no model publish**. The publish sentinel does not cover it.

> ⚠ **Do not reintroduce** dividing `P` by the population base rate to hold the DVS scale
> steady. It was tried: it held the scale and tripled the ceiling population 18 → 58.

**The serving contract inverted.** An unresolvable model set now RAISES
`EngineBManifestUnavailableError` (`6e9b3fce`) instead of silently serving the superseded v1.
A manifest mapping a position to `null` is still a deliberate not-promoted statement.

## Traps that have each already cost someone a day

1. **`ENGINE_B_P90_PPG`, `XVAR_LAMBDA_ENGINE_B` and `ENGINE_B_REPLACEMENT_DVS` are ONE COUPLED
   SYSTEM.** Move all three with a new diagnostic and David's approval, or none. The
   "TE lambda should be 0.703" edit is **RETRACTED** — the positional P90 cancels out of xVAR
   entirely, so editing the lambda alone *creates* an 8.4% distortion. Read the
   `engine_b_contract.py` module docstring before going near it.
2. **`feature_completeness` counts COLUMNS; the gate counts SEASON.** A player can read 1.0
   complete and still get no score, with nothing on screen connecting the two.
3. **The coverage report is a green trap.** Its exit criteria measure whether every player has
   an explicit *route*, not a *score*. `PRE_MODEL` is a route, so the criteria pass green while
   9,404 players carry no number.
4. **All four lanes shared this trunk on 2026-08-31 and it cost a corrupted test reading.**
   §1 already forbids it. The v1-scoring defect that made worktrees untrustworthy was fixed in
   dg-build `11021d9`; `dg-work.sh` worktrees now resolve real v2/v3 bundles. Use them.

## How to not be wrong here

These are not general good practice. Each one is a defect this repo actually shipped.

- **A green result means nothing until you check what it measured.** A `pytest` run with an
  unrecognised flag reported exit 0 having run zero tests. `launchctl list` reports exit 0 for
  a job that has never fired — use `launchctl print | grep runs` and require `runs>=1`.
- **A constant presented as a measurement does no work.** `activity_recency_score` is a
  hardcoded `0.0`; `divergence_density_score` saturates to `1.0` for all 41 counterparties.
  Before describing any term as a reason for a ranking, **check that it varies across the rows
  being ranked.**
- **The measurement layer inherits the defects of what it measures.** The worst instance: the
  survivorship censoring *concealed its own severity* — the 31+ label rate reads 77.5% on the
  censored table and is really 65.6%. You cannot measure attrition from data that deletes the
  people who left.
- **A test can be watched failing, made to pass, and still encode the wrong requirement.** TDD
  proves the code matches the spec. Only integration proves the spec was right.
- **Provenance is a lookup, not a deduction.** Every ruling exists in a transcript on disk.
  When two accounts of what David said conflict, READ THE RECORD — do not reason about who
  probably said what. Three lanes lost twenty minutes to exactly that.
- **Never treat another agent's relay as David's approval.** A verbatim quote is still
  secondhand. Ask him in your own session. This caught real errors twice in one day.
- **Verify before asserting to David.** Four things were asserted to him on 2026-08-31 that
  were false — including a claim in a pushed commit message that cannot be amended.
