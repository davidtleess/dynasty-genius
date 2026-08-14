# Realized-Outcome Scorer Wiring — Codex Adversarial Framing Review v1

**Cycle:** TW0813-SCORER-1 · **Date:** 2026-08-13 · **Lane:** Codex review  
**Reviewed artifact:** `realized_outcome_scorer_wiring_framing_claude_v1.md`  
**Reviewed SHA-256:** `cfdf021a376622219fa9e1728bf01260854a96b5d6a96f19535a9d895759f38c`  
**Verdict:** **NOT CLEAR — four BLOCKERs, three WARNs.**

This is a framing/contract review, not a product-code change. The current +98-line
prediction-loader diff is inside scope because its author explicitly routed it for independent
review. No commit, push, scheduler action, provider contact, declaration, or Studio inspection
occurred.

## Findings

### B1 — BLOCKER: Q5 silently truncates the frozen cohort and drops the entire prediction-time utilization payload

The five-key join is correct but the proposed contract stops too early. On the recommended
2026-06-28 capture, the store contains **583 model-supported joinable rows** (503 Engine B +
80 Engine A). The companion table classifies **503** as `prediction_ppg_status=captured` and
**80** as `capture_incomplete/missing_feature_row`. The current query filters to `captured`
and returns 503 rows with no count or status for the 80 omitted model-supported rows. That
violates the realized-outcome design §4.1 requirement that post-rollout incomplete captures
fail closed **with an exclusion count**; it also makes the frozen-set denominator invisible.

The query selects only `sleeper_id`, `capture_date`, `projection_2y`, and `position`. It does
not select or parse `s.utilization`, `util_snapshot_status`, `schema_version`, or `source_hash`.
All 503 captured rows contain valid utilization JSON. Because the scorer iterates
`prediction.get("utilization") or {}`, the result is an empty MIF object, not the framing's
claimed per-field `unavailable` state. The existing injected-fixture tests hide this because
their synthetic predictions already carry `utilization`.

**Required framing/RED correction:** Q5 remains in scope, but the contract must pin the full
frozen-set denominator, named counts for each excluded prediction status, parsed/validated
prediction-time utilization with its roles and provenance, and the cross-component shape
delivered to `score()`. A `captured`-only filter without the omitted-status accounting is not
an honest frozen-set loader.

### B2 — BLOCKER: Q3 does not cover the actual model-input fields in the frozen substrate

Q3 frames realized utilization as snap share, route participation, and target share. That is
the outcome store's current three-field schema, but it is not the prediction snapshot's actual
role contract. In the 503 captured 2026-06-28 rows:

- `snap_share` is `model_input` for 503 rows (502 valued);
- `weighted_opportunity`, `yprr`, and `tprr` are each `model_input` for **315** receiver rows;
- route participation and target share are diagnostic-only in this frozen model.

`realized_outcome_scorer._UTIL_FIELD_TO_REALIZED` only maps snap share, route participation,
and target share. Even after B1 is fixed, 315 rows' WOPR/YPRR/TPRR model-input fields have no
realized counterpart and will read `unavailable`. The proposed snap-only RED therefore does
not test the principal MIF gap present in the real frozen payload.

**Required framing/RED correction:** enumerate every `role=model_input` field observed in the
declared frozen set and pin its realized-source status individually. A deliberately unavailable
field is honest; an unmentioned model input is not. If this increment intentionally ships only
snap-share MIF, the artifact and contract must say it is a partial MIF wiring and must prove the
other model-input fields remain explicit `unavailable`, never absent or silently downgraded.

### B3 — BLOCKER: the framing omits the production path's survivorship-completeness failure

The design §4.3/§6 requires every captured player to remain represented, including explicit
zero-game rows for injured, cut, benched, bye, not-yet-played, or departed players. The current
default stats loader emits only rows present in `load_player_stats`, then stamps every emitted
row `player_status="active"` and `game_played=True`. `_build_outcomes` seeds its player universe
only from those stat rows. A frozen player absent from the weekly stats feed never receives a
weekly fact; `score()` marks it `missing_outcome` and does not increment cohort membership.
Consequently the path cannot distinguish bye/injury/departure and can silently remove failed
picks from rank cohorts. This is not in the three traps or nine seed families.

**Required framing/RED correction:** add a frozen-player-with-no-stat-row seed and require an
explicit zero-game fact/status plus retained cohort membership. Add bye, injury, departure, and
not-yet-played variants, and prove the loader does not default every observed row to active/played
without evidence.

### B4 — BLOCKER: Q2(b) is a delay heuristic, not the locked all-games-final evidence contract

The base design locks finality as: every expected game has terminal evidence; any missing,
postponed, or unknown game means `not_finalized`. B21 explicitly says a populated score proves
only `result_observed_unverified`. Waiting N days after gameday reduces the chance of catching an
in-progress game, but it does not turn unverified observation into terminal evidence. A suspended,
postponed, corrected, or missing game can cross the window unchanged. Labeling the basis does not
make `week_status=finalized` true.

The current board also leaves this consumer rewiring **OPEN FOR DAVID**. Cockpit agreement cannot
convert that open decision into build authority. I therefore rule out Q2(a), Q2(b), and Q2(d)
under the current contract. Of the listed choices, only **Q2(c)** supplies governed terminal
evidence. An independently authoritative terminal-status source would also satisfy the contract,
but it is not among the options and would require its own authorization. A stability window may
remain a conservative precondition, never the proof of finality.

### W1 — WARN: the zero-coverage guard is necessary but not sufficient

`graded == 0 && predictions > 0` catches the exact empty-bridge defect, but a run grading 1 of
503 predictions would still terminate `ok`. The scorecard lacks root denominators for declared
predictions, loader-eligible predictions, identity-resolved predictions, outcome-present rows,
and rank-eligible rows. Add a catastrophic-partial-coverage seed and explicit coverage fields.
Any threshold that changes `ok` to degraded/failed is a product contract requiring a stated
basis; do not silently invent one. The nominal pinned crosswalk probe is encouraging—503/503
captured 2026-06-28 sleeper IDs resolve, with zero duplicate sleeper→GSIS or GSIS→sleeper
conflicts—but nominal coverage does not replace the adversarial contract.

### W2 — WARN: Q1(a) needs exact provenance and canonical-ID assembly rules

The pinned `ff_playerids` file is usable for the immediate frozen set: it was pulled
2026-05-16T03:28:22Z, SHA-256
`8ed4b67578d06a24527356f9f355ed97f12be827e34885270c0b1d28c079f593`, and resolves all
503 currently captured frozen sleepers. But an adapter built at scoring time must stamp the
**source pull timestamp**, not the scoring request time; otherwise the bridge falsely claims a
new point-in-time observation. It must also retain the frozen capture's 503 distinct nonblank
`model_forward_capture_joinable.dg_player_id` values rather than inventing a Dynasty Genius ID
from an ff crosswalk that does not carry one. Pin source hash, pull timestamp, mapping version,
DG-ID provenance, and duplicate/conflict behavior in RED.

My Q1 ruling is therefore **Q1(c), conditionally**: use the pinned crosswalk now only under those
provenance rules; record forward identity capture as a separately authorized follow-up, not as
authority granted by this cycle.

### W3 — WARN: declaration seeds omit required wrong-type and malformed-shape cases

The robustness matrix explicitly includes wrong-type and malformed-shape inputs. Current
`_load_frozen_declaration` calls `.get` on the top-level value, `seasons`, and season entry
without first proving each is an object. Lists/strings therefore escape as generic
`AttributeError` and are collapsed by `run_scoring` to `predictions_load_failed:AttributeError`.
Extend seed 3 with non-object root, non-object `seasons`, non-object season entry, invalid date/
timestamp types and formats, duplicate JSON keys, and unexpected member types. Failures should
be named declaration-contract failures, not incidental interpreter exceptions.

## Q1–Q5 disposition

- **Q1:** conditional (c): pinned crosswalk now with source-time/SHA/DG-ID provenance; forward
  capture only as a separately authorized follow-up.
- **Q2:** (c) under current authority, or a separately authorized authoritative terminal-status
  source. Rule out (a), (b), and (d) as evidence of finality.
- **Q3:** snap share may be the smallest partial increment, but the contract must enumerate the
  real WOPR/YPRR/TPRR model-input gaps and label the result partial MIF wiring.
- **Q4:** (b), with an exact gameday-age boundary and ordinary pre-boundary no-op pinned. This is
  narrower than changing the general freshness schema and preserves honest off-season no-op.
- **Q5:** yes, expanded per B1 and W3; the current +98-line diff is not independently clear.

## Checks and probes run

- Re-read the framing and independently matched its SHA-256.
- Inspected the full `scripts/run_realized_outcome_scoring.py` diff (+98 lines; 95 additions,
  3 deletions), the pure scorer, identity bridge, prediction snapshot store, outcome store,
  freshness evaluator/config, base design, implementation plan, and relevant contract/unit tests.
- SQLite read-only probes over `model_forward_capture.db` and `nflverse_usage.db`: table schemas,
  capture/status counts, five-key join cardinality, blank IDs, utilization JSON validity/roles,
  Engine A/B cohort counts, and snap-count substrate shape.
- Pinned ff-playerids probes: source timestamp/hash, usable-ID counts, duplicate/conflict counts,
  and frozen-set coverage (503/503).
- Declaration existence probe: absent, consistent with DG-09 remaining David's decision.
- `git diff --check -- scripts/run_realized_outcome_scoring.py`: pass.
- `.venv/bin/python3.14 -m py_compile` on the CLI/scorer/bridge: pass.
- Focused existing suites: **34 passed**, two known scipy warnings.
- Ruff could not run through the venv because the module is not installed there; no alternate
  environment was installed or mutated for this review.
- Dirty-tree review preserved unrelated user/agent work. No source store was written.

## Loop-control disclosure

The abandoned Footballguys v22 run has been truthfully terminated as `BLOCKED` because its old
required checks were absent. It no longer prevents TW0813-SCORER-1 initialization. At the time
this artifact was authored, no scorer run had yet replaced it, so these findings could not be
recorded against an active scorer round without clobbering another lane's ownership. Claude was
notified through the cockpit, and delivery was positively verified in its transcript.
