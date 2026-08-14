# Realized-Outcome Scorer Wiring — Framing v3 + round-2 disposition (Claude, 2026-08-14)

**Cycle:** TW0813-SCORER-1 · **Supersedes:** v2 (`e31a583c…`) as amended by the DG-09 addendum
(`8e763d5e…`). **Folds:** Codex round-2 review
(`realized_outcome_scorer_wiring_framing_v2_review_codex_v1.md`, `dcd12344…`) — R2-B1..B4 and
R2-W1, ALL ACCEPTED after independent verification of every citation. v2 stands except where
this document amends it. **RED authorship: Codex** (02 default + the ratified outcome plan —
its claim is correct and adopted; Claude owns GREEN).

## Round-2 dispositions (each citation re-verified by this lane before acceptance)

- **R2-B1 — ACCEPT; realized WOPR is OUT of this cycle.** Verified:
  `test_ff_opportunity_ingestion_red.py:339-358` bans ANY `ff_opportunity` symbol reference in
  `src`/`scripts`/`app` outside the adapter — the ban is symbol-level, so even the SQL string
  in the scorer would trip it. `ff_opportunity` is a third-party model output requiring its own
  validation before any consumer; that validation + boundary amendment is a **separately
  authorized follow-up**, not this cycle. Realized utilization this cycle is therefore
  **snap-share ONLY**, from `player_snap_count` — verified to carry NO consumer cordon — and
  every other realized-util field is explicit `unavailable`. The scorer's consumption of
  `player_snap_count` is a **recorded disposition change** (substrate_only → existing_consumer:
  reader = the scorer's util loader; permitted use = realized snap-share for descriptive MIF),
  owned by this David-approved cycle and pinned in RED.
- **R2-B2 — ACCEPT; the v2 anchor was a stale comment, and citing it was this lane's error.**
  Verified: the shipped formula is `assemble_engine_b_dataset.py:203-205` —
  `1.5*target_share + 0.7*air_yards_share`, zero denominators → NaN via `replace(0, nan)`,
  then `fillna(0)`; the comment at `engine_b_contract.py:117` ("target_share ×
  air_yards_share") contradicts it. With WOPR out of this cycle (R2-B1) the parity pin is
  moot here; the stale comment is recorded on the run backlog for a separate one-line repair
  (WARN-class; not this cycle's files). Any FUTURE realized-WOPR contract pins formula, grain,
  aggregation, zero-denominator and fillna semantics against the assembly code, never a
  comment.
- **R2-B3 — ACCEPT; honest-status contract, no fabricated statuses.** Verified: frozen
  joinable rows carry no team; the default stat loader emits only stat-present players with
  hardcoded `active`/`game_played=True`. Resolution: the OutcomeRow `player_status` vocabulary
  gains **`status_unverified`** (a contract change, reviewed in this cycle's RED). Precedence,
  closed and total: stat-present week → `active` (observed play); stat-absent week for a
  frozen-cohort player → an EXPLICIT zero-game weekly fact with `status_unverified` — never
  bye/injured/departed/not-yet-played, because no governed source distinguishes them today.
  Every frozen player is retained in every cohort denominator. Survivorship-floor logic never
  treats `status_unverified` as a verified departure (no floor claim without a verified
  status). Wiring the REAL status substrates (`nflverse_injury_report` — 34,812 rows —
  and `depth_charts`, each needing its own consumer disposition) is a named follow-up, not
  this cycle.
- **R2-B4 — ACCEPT; the boundary is now exact.** Amended Q4(b): while `week_status !=
  finalized`, if `(now.date() − latest parseable gameday of the target week).days` **strictly
  exceeds 14**, the run terminates `failed` with reason `week_nonfinal_overdue` (carrying
  `week_status` and the gameday); at exactly 14 or less it remains the healthy
  `week_not_finalized` noop. **Basis: 14 is `SCHEDULED_TARGET_MAX_AGE_DAYS`, the already
  shipped and cockpit-cleared freshness constant (spec 2026-07-11 §2.2) — one basis, no new
  number.** Gate order: evaluated on the nonfinal branch BEFORE the noop return, on BOTH the
  scheduled and explicit paths (a backfill target that never finalized is the same anomaly).
  Unparseable or absent gamedays on that branch fail loud (`nonfinal_age_indeterminate`),
  mirroring `target_freshness_indeterminate`. RED mutation-tests both sides of the boundary.
- **R2-W1 — ACCEPT.** The RED pins an **injected finality-evidence interface** only; choosing
  or authoring the real provider/mechanism stays David-gated (Q2(c) unchanged).

## Corrections of record adopted from round 2

- **Grading denominator = 581** model-supported joinable rows on the declared `2026-08-05`
  (501 Engine-B `captured` + 80 Engine-A `capture_incomplete`) — re-verified by this lane's
  own probe this round. 12,209 is the unfiltered snapshot universe and must never appear as a
  grading denominator. Contracts bind denominators to the DECLARED capture via the
  declaration file at runtime; no candidate-date count is hardcoded.

## What GREEN will change (consolidated scope for the RED, Codex-authored)

1. Prediction loader (B1 family): 581-denominator + per-status exclusion counts + parsed/
   validated per-field utilization with roles/provenance into `score()`.
2. Identity loader: pinned-crosswalk adapter under W2 provenance rules (source pull time
   `2026-05-16T03:28:22Z`, SHA `8ed4b675…`, `dg_player_id` preserved, duplicate/conflict
   pinned), via canonical `_load_ff_playerids`.
3. Util loader: `player_snap_count` snap-share only (pfr→gsis via crosswalk; unresolved →
   `unavailable`); all other fields explicit `unavailable`; partial-MIF labeling.
4. Outcome universe: frozen-cohort seeding + `status_unverified` contract (R2-B3 above).
5. Nonfinal-overdue gate: R2-B4 exactly as pinned above.
6. Coverage: zero-graded → `failed`; denominators on scorecard + marker; catastrophic-partial
   seed; no invented partial bands (David's).
7. Declaration seeds (W3) and finality injected-interface seeds (R2-W1).
8. No-Verdict + read-only law rows unchanged from v2 §5.8–5.9.

## Standing

DG-09 CLOSED by David's word (`2026-08-05`; declaration `77544b3b…`, loader-verified 501).
No push · commits via gate paths only · no scheduler · no provider contact · no live
nflreadpy in TDD · Studio wall intact · frozen pairs untouched. The 2026-08-12 capture gap is
a tracked separate layer-1 health item. H2 QB rushing remains a registered hypothesis
**UNDER TEST** with no result.
