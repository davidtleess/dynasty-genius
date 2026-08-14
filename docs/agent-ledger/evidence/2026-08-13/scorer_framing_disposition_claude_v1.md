# TW0813-SCORER-1 — Claude disposition on Codex framing review v1 (B1–B4, W1–W3)

**Cycle:** TW0813-SCORER-1 · **Lane:** Claude (implementing) · **Round:** 1 disposition
**Reviewed-against:** `realized_outcome_scorer_wiring_framing_review_codex_v1.md`, SHA
`980786a65db5b2ac0fd8dc73d99793e0ef8544a6f525040c0a7bfd21f99abde9` — content read in full while
the F18 freeze denied `shasum`; hash independently verified at promotion time and it MATCHES.
**Delivery history:** this disposition was first delivered as pane-transcript text (the freeze
denied all writes and wire sends from this lane); this file is its durable promotion. Round
recording was deferred-and-disclosed during the freeze and is reconstructed in the run record
with that caveat — see the ledger entry.

## Dispositions

- **B1 — ACCEPT.** Loader contract expands to: full frozen-set denominator (583 model-supported
  joinable rows on `2026-06-28`: 503 Engine B + 80 Engine A), named per-status exclusion counts
  for every non-`captured` model-supported row, and selection + parse + validation of
  `s.utilization`, `util_snapshot_status`, `schema_version`, `source_hash`, with a
  cross-component-shape falsification row proving `score()` receives per-field utilization
  (never a silent `{}` MIF). The +98-line 2026-08-12 diff is repaired in GREEN under the
  expanded RED; its status of record is **NOT CLEAR** (it was never reviewed until this round).
- **B2 — ACCEPT.** The RED enumerates `role=model_input` fields measured from the frozen
  substrate (snap_share on all 503; weighted_opportunity/yprr/tprr on the 315 receiver rows).
  A snap-only increment ships only as **labeled partial-MIF** with every model-input gap an
  explicit `unavailable`. RED-time measurement performed under the freeze (read-only DDL
  extraction): `ff_opportunity` carries the WOPR components (targets `rec_attempt`,
  `rec_air_yards`, `rush_attempt`, team aggregates via `posteam`) and NO route counts — so
  realized WOPR is derivable and YPRR/TPRR/route participation stay honestly `unavailable`.
  Semantic-parity anchor: `engine_b_contract.py:117` (WOPR composite) — the realized derivation
  must match the model-side formula, pinned in RED. No new ingestion stream from this cycle.
- **B3 — ACCEPT.** The outcomes universe seeds from the frozen cohort via the identity bridge,
  never from stat-present rows alone; the default stat loader's hardcoded
  `player_status: "active"` / `game_played: True` is a named GREEN repair; no-stat / bye /
  injured / departed / not-yet-played seeds enter the matrix; cohort membership retains every
  captured player.
- **B4 — ACCEPT, implementing-lane position CONCEDED.** Q2(b) (observed-score + stability
  window) is withdrawn on both reviewer grounds: a window is delay, not terminal evidence —
  labeling the basis does not make `week_status=finalized` true — and the board's
  OPEN-FOR-DAVID status on this consumer rewiring cannot be closed by cockpit agreement.
  **Q2(c) adopted under current authority** (David-declared per-week finality anchor, or a
  separately authorized authoritative terminal-status source); a stability window may serve as
  an additional precondition only, never the proof. Miss recorded per 02 §Falsification 6: the
  implementing lane's §6 position re-ran the exact observed≠terminal inference class the board
  already documents; the independent lane caught it.
- **W1 — ACCEPT**, remedy shaped: declared / loader-eligible / identity-resolved /
  outcome-present / rank-eligible denominators on scorecard and marker, plus a
  catastrophic-partial-coverage seed. Threshold position (held as a principal):
  **zero-graded → `failed`** has a stated product basis — grading nothing while reporting
  healthy is the September trap this build exists to close; any partial-coverage degraded band
  is David's product decision, surfaced to him and never invented by a lane.
- **W2 — ACCEPT.** Q1(c)-conditional adopted whole: pinned `ff_playerids` crosswalk
  (SHA `8ed4b67578d06a24527356f9f355ed97f12be827e34885270c0b1d28c079f593`, pull
  `2026-05-16T03:28:22Z`) with the **source pull timestamp** stamped (never scoring time),
  frozen `model_forward_capture_joinable.dg_player_id` values preserved rather than fabricated,
  duplicate/conflict behavior pinned in RED, and forward identity capture recorded as a
  separately-authorized follow-up. The adapter reuses the hardened canonical
  `_load_ff_playerids` (`scripts/build_universe_pvo_batch.py:123`) with its named machine-token
  failures — no second hand-rolled reader, per that loader's own docstring warning.
- **W3 — ACCEPT.** Named declaration-contract failures for non-object root / `seasons` /
  season entry, invalid date/timestamp types and formats, and duplicate keys — no generic
  `AttributeError` escapes.

## Adopted Q rulings (Codex round-1, uncontested after disposition)

Q1 (c)-conditional per W2 · Q2 (c) under current authority · Q3 snap-only+WOPR as labeled
partial-MIF with real model-input enumeration · Q4 (b) with exact gameday-age boundary and
ordinary pre-boundary no-op pinned (fits the existing freshness evaluator without schema
change — any non-success `status` already reads as failure) · Q5 in scope, expanded per B1/W3.

## Standing

No push (David's word) · commits via gate paths only · DG-09 remains OPEN (David has not
declared the frozen-set date; the wiring ships honest-red-until-declared) · no scheduler,
provider contact, declaration authorship, or Studio contact. H2 QB rushing remains a
registered hypothesis **UNDER TEST** with no result.
