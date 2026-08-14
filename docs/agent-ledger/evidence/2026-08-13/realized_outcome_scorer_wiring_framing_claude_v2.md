# Realized-Outcome Scorer Wiring — Framing v2 (Claude, 2026-08-13/14)

**Cycle:** TW0813-SCORER-1 · **Supersedes:** framing v1
(`cfdf021a376622219fa9e1728bf01260854a96b5d6a96f19535a9d895759f38c`).
**Folds:** Codex adversarial review v1
(`realized_outcome_scorer_wiring_framing_review_codex_v1.md`,
`980786a65db5b2ac0fd8dc73d99793e0ef8544a6f525040c0a7bfd21f99abde9`, verified) — B1–B4 and
W1–W3 all ACCEPTED per `scorer_framing_disposition_claude_v1.md`; Codex's Q rulings adopted
uncontested. **Authority:** David's approved scorer-wiring build (2026-08-09 23:10) +
TW0813-AUTONOMY-1 (build·review·judge·ship in bunches; DG-09 open; no push).
**Provenance note:** v2 was first authored as pane-transcript content while the F18 freeze
denied writes; this file is its durable promotion, extended only by the freeze-era read-only
measurements recorded in the disposition.

## §1 Situation

First finalized week of September 2026: the product must grade the frozen pre-season model
against reality — the constitution's trust layer ("Backtesting is a trust layer, not optional
QA"). As shipped, the scheduled job reports healthy while grading nothing.

## §2 Measured state (shared factual base, both lanes)

Frozen-set candidate `2026-06-28`: **583 model-supported joinable rows** (503 Engine B + 80
Engine A); **503 `captured`**, 80 `capture_incomplete`/`missing_feature_row`; all 503 carry
valid utilization JSON (snap_share `model_input` ×503; WOPR/YPRR/TPRR `model_input` ×315
receiver rows). Identity: pinned `ff_playerids` (SHA `8ed4b675…`, pulled
`2026-05-16T03:28:22Z`) resolves **503/503** frozen sleepers, zero duplicate/directional
conflicts; frozen joinable rows carry 503 distinct non-blank `dg_player_id` values (preserve,
never fabricate). Realized substrate: `player_snap_count` has `offense_pct`, identity-resolved
but **pfr-keyed** (bridge to gsis via the crosswalk; unresolved → `unavailable`);
`ff_opportunity` carries WOPR components and **no route counts** (full DDL recovered) — so
YPRR/TPRR/route participation stay `unavailable`. WOPR semantic anchor:
`engine_b_contract.py:117`. Declaration file absent (DG-09, David's — ships honest-red).
`noop` ∈ `success_status` on the auxiliary tier. The 08-12 +98-line prediction-loader diff
stands **NOT CLEAR**.

## §3 The traps (review folded)

**(A) Coverage:** an empty bridge yields an `ok` scorecard grading zero — and a 1-of-503 run
would too; the guard is denominators plus a zero-graded failure, not a lone zero-check.
**(B) Finality:** a populated score is `result_observed_unverified`; nothing this lane builds
converts observation into termination — only governed terminal evidence does.
**(C) Health:** in-season `week_not_finalized` beyond a bounded gameday age must stop reading
as healthy.

## §4 Rulings adopted

- **Q1 → (c) conditional:** pinned-crosswalk bridge now, under W2 provenance rules —
  source-pull timestamp stamped (never scoring time), source SHA + mapping version pinned,
  frozen `dg_player_id` preserved, duplicate/conflict behavior pinned in RED; adapter reuses
  canonical `_load_ff_playerids` (`build_universe_pvo_batch.py:123`); forward identity capture
  is a separately-authorized follow-up.
- **Q2 → (c) under current authority:** the finality gate consumes a David-declared per-week
  finality anchor (or a separately authorized authoritative terminal-status source); a
  stability window is at most an additional precondition. (a)/(b)/(d) ruled out as evidence
  of finality.
- **Q3 → snap-share + WOPR as explicitly-labeled partial-MIF:** contract enumerates the real
  `model_input` set (incl. the 315-row WOPR/YPRR/TPRR receiver cohort); realized WOPR derived
  from `ff_opportunity` under pinned semantic parity with `engine_b_contract.py:117`; every
  unsourced field explicit `unavailable`; no new ingestion stream from this cycle.
- **Q4 → (b):** producer-side split with an exact gameday-age boundary — in-season
  `week_not_finalized` older than the pinned bound becomes `failed`; ordinary pre-boundary
  no-op pinned healthy; freshness evaluator and schema untouched (any non-success `status`
  already reads as failure).
- **Q5 → in scope, expanded:** the RED covers the 08-12 diff's full contract — B1's
  denominator + per-status exclusion counts + parsed/validated utilization, provenance
  fields, and the cross-component shape into `score()`.

## §5 RED contract families (v1 seeds 1–9 expanded by B1–B3/W1/W3)

1. **Coverage:** zero-graded→`failed` (stated basis: the September trap); catastrophic-partial
   seed; declared/eligible/resolved/outcome-present/rank-eligible denominators on scorecard
   AND marker; no invented partial bands — those are David's.
2. **Prediction loader:** 583-denominator with named per-status exclusion counts;
   `captured`-only rows carry parsed per-field utilization with roles; malformed/wrong-type
   util JSON → named failure; declaration seeds per W3 (named contract failures for non-object
   root/`seasons`/entry, invalid date/timestamp types/formats, duplicate keys).
3. **Identity:** provenance-stamped bridge (source pull time, source SHA, mapping version);
   empty/conflict/duplicate seeds; `dg_player_id` preservation; unresolved → excluded and
   counted, never guessed.
4. **Outcomes:** universe seeded from the frozen cohort; explicit no-stat/bye/injured/
   departed/not-yet-played facts; hardcoded `active`/`game_played=True` repaired; pfr→gsis
   bridging for snap rows with unresolved → `unavailable`.
5. **Finality:** gate consumes only the governed anchor (Q2(c)); interim-score seed; missing/
   postponed game → `not_finalized`; anchor absent → honest non-finalized, never inferred.
6. **Freshness/health:** Q4(b) boundary mutation-tested on both sides of the pinned age.
7. **MIF:** partial-MIF labeling; per-field `unavailable` for every unsourced model-input;
   WOPR semantic-parity pin; never imputed, never derived from a different formula.
8. **No-Verdict:** `decision_supported=False` recursively; marker execution-state-only;
   banned-language scan on scorecard and marker.
9. **Read-only law:** source stores opened `mode=ro`; temp outcome store auto-cleaned;
   `subprocess`/git-forbidden seam intact.

## §6 David-gated items this build surfaces (decision packet, via Tower)

1. **DG-09** frozen-capture declaration — OPEN; scorer ships honest-red until declared.
2. **Q2(c) finality-anchor mechanism** — weekly declaration by David, or authorizing an
   authoritative terminal-status source as separate layer-1 work (weekly-cost tradeoff stated).
3. Optional partial-coverage degraded bands — default is disclose-only until he rules.
4. Push — bunches accumulate as local commits per TW0813-AUTONOMY-1.

## §7 Not doing

No push · no scheduler · no provider contact · no live nflreadpy in TDD · no declaration
authorship · no Studio contact · frozen wire pair and v26 pair untouched · no new ingestion
streams. H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result.
