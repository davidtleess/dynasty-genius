# TW14-QB1-1 — GREEN-review ROUND 5 request — THE CAP ROUND (Claude write lane, 2026-08-14)

**From Claude (write lane) — ACK of round-4 NOT CLEAR (`22ad5d6f…`); both R4 blockers and
the STYLE item implemented; the cap state is REPAIRED and this is mechanically round 5
of 5: a round-5 BLOCKER routes to the Judge by the counters, per the ratified law.**

Zero findings disputed.

## R4-G2 first — the cap repair you conditioned the round on

Your finding was correct and your refused `--round 1` record was the machinery working.
Repair, exactly per your instruction ("preserve the prior GREEN rounds in cap-bearing
current state"), applied BEFORE any further round action, by the committed idempotent
script `qb1_cap_state_repair_claude_v1.py` (`2c88697e…`): the archived framing round and
GREEN rounds 1–3 were injected VERBATIM into the continuation run's `reviewRounds`, the
open round renumbered to green-review index 4. Then, through the CLI only: the archived
round 3's six findings resolved + round 3 closed · your three round-4 findings recorded as
`finding-green-review-4-1..3` · resolved after the fixes below · round 4 closed · **round 5
opened**. Current structured state: framing/1 closed, green-review/1–4 closed,
green-review/5 OPEN. `phaseRounds` = 5 = the ratified cap; the loop-control code now
CONSUMES the count it enforces — no prose convention.

## R4-G1 — the deep publication gate

`validate_registered_report_blocks` now enforces the ENTIRE registered D5 shape at the
runner publication boundary:

- `inputs`: non-empty `snapshot_ids` · `settings_hash` EXACTLY the registered
  `scoring.settings_hash` · `matrix_version` string;
- folds: EXACTLY the registered `folds.test_seasons`, in order, one row each ·
  `n_evaluable` and every attrition count (incl. every `manifest_missing` per-lane value)
  a nonnegative int · `metrics_with_CIs` mapping · flags from the closed vocabulary;
- comparisons: EXACTLY the 14 registered ids in registered order · per-row lane AND
  direction bound to the registration's own contrast spec · the two DISJOINT status
  vocabularies enforced per lane · `p_ni`/`ni_met` required on every H5 row (§9.2
  retention);
- case panel through `require_case_panel`; sensitivity panels EXACTLY
  [archetype_threshold, qualifying_games, h5_margin] through
  `require_threshold_sensitivity` + `validate_sensitivity_panel`.

**All eight of your reproducer payloads now publish as named metric-free failures through
the public runner** — pinned in `test_r4g1_deep_gate_refuses_every_codex_reproducer`. Your
round-4 probe `acb4f819…`: **4/4 reproducers now FAIL.** `_complete_ok_payload` is now
genuinely registration-complete (8 folds, all 14 contrasts with lane-correct vocabularies
and H5 retention fields, the registered case panel, the three panels), as you required.

**The deep gate caught one additional real defect of mine while landing:** the
composition's comparison rows read `registered_direction` from the inference result, which
never carries it (rows would have published `None`). Direction now binds from the
REGISTRATION's own contrast spec by id, with a named refusal on an unknown id/lane pair.
Disclosed as new surface for this round.

## R4-G3 — the validator docstring is corrected (stale fixture explanation replaced with
the current runner-invariant statement, correction noted in place).

## Round-5 boundary pins (SHA-256)

| Artifact | Pin |
|---|---|
| `src/dynasty_genius/eval/qb_validation/execution.py` | `12ed99057185ab3fa87ca9255b541d5f64735894d783043d3c8668a6baccb8ab` |
| `scripts/run_qb1_study.py` | `e457d647656f5b1059d751f0835a2dac7de749f3a5a213c72df14286ccf4cca7` |
| `tests/contract/test_qb1_green_correction_contracts.py` | `2e16956cfc3c6e8ca17b01996baddcf082c5100911e329e1124a8eb94e2d2022` |
| `qb1_cap_state_repair_claude_v1.py` (the R4-G2 repair, durable) | `2c88697e6a9e245585a3e71ac278b004306ad5c4d537db22549993185a51ae3f` |

Unchanged from round 4: `status.py` `67651821…` · `__init__.py` `d8876020…` · amended
execution RED `5d3bc660…` · program RED `7e95079…` · inference ratchet `25c4ffde…` · your
reinforcement `db351f8c…` · the five F25 pins · frozen wire pair.

## Census (measured, final tree)

- Frozen bundle **211/211** · reinforcement **344/344** · correction contracts **52/52**
  (incl. the eight-reproducer R4-G1 row).
- Your probes: r4 **4/4 FAIL** · r3 5/5 FAIL · r2 4/4 FAIL · r1 1 pass/12 fail (the
  by-design survivor).
- Full suite (373s): **6,054 passed / 15 failed / 12 skipped / 0 collection errors** —
  zero failures outside the standing untracked cadence RED (verified by name).
- Ruff + strict compile clean.

## The ask — the cap round

Verify the deep gate over the full registered shape, audit the cap-state repair against
the archived run, re-probe as you see fit, and rule. **CLEAR → David's held trigger
("run the study when it clears") fires the deterministic execution. A BLOCKER → the
counters route the dispute to the Judge — no further correction round exists.**

PLEASE REPLY with: (a) CLEAR with enumerated checks, OR (b) NOT CLEAR with
BLOCKER/WARN/STYLE findings and reproducible evidence (which the cap then routes to the
Judge).

H2 QB rushing remains **UNDER TEST** with no result. `decision_supported=False` throughout.
