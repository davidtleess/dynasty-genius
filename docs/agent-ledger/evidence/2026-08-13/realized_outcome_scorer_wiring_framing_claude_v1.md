# Realized-Outcome Scorer Wiring — Framing v1 (Claude, 2026-08-13)

**Cycle:** TW0813-SCORER-1 · **Authority:** David's approval of the scorer-wiring build
(2026-08-09 23:10, carried by Tower's dispatch) + his standing word via Tower today ("get the
team working on something"). **This framing creates no commit, push, scheduler, capture, or
provider-contact authority.** Loop-control is ACTIVE for this cycle (5 rounds/phase, 10/run);
round recording is deferred until Codex disposes its own abandoned `run.json`
(`ba1a6467…`, Footballguys v22, flagged in today's 00:15 ledger entry) — its run, its `finish`.

**Layer:** 3 presenting (models — benchmarking against real results as they land). The
layers-1/2 dependency check is in today's 22:59 ledger preflight; its two substrate gaps
(route participation, governed identity snapshots) are design questions §4 below.

---

## 1. The concrete manager situation this serves

September 2026, the Tuesday after the first finalized NFL week. David logs in and the product
should be able to answer: *how did the frozen pre-season model's predictions hold up against
what actually happened?* The constitution makes this non-optional: "Backtesting is a trust
layer, not optional QA … Model credibility is earned through validation and backtest
visibility" (00 §Locked Analytical Rulings). The Realized-Outcome Loop (T1–T5, shipped PR #90,
scorer fixed #147/#148) is that trust layer's weekly engine — and today, as wired, the
scheduled job would report **healthy all season while grading nothing**.

## 2. Measured current state (all probes read-only, rerunnable)

| Piece | State | Evidence |
| :-- | :-- | :-- |
| Prediction loader | **WIRED 2026-08-12 (session 7f9a8a50) — UNREVIEWED, UNCOMMITTED** (+98 lines in tree). Declaration-gated; raises `FrozenPredictionSetUndeclared` → exit 1 rather than noop. | `git diff scripts/run_realized_outcome_scoring.py`; handoff `docs/agent-ledger/evidence/2026-08-12/session_7f9a8a50_closeout_handoff_v1.md` item 2 |
| Frozen-set declaration | **ABSENT** — `app/config/realized_outcome_frozen_predictions.json` does not exist. DG-09: David's decision (recommended `2026-06-28`, the pre-season capture). Until declared the job exits 1 — deliberately. | `ls app/config/` |
| Prediction substrate | 23,070 `captured` rows, 46 capture dates `2026-06-28`→`2026-08-13` in `model_forward_capture.db` | sqlite ro probe, 2026-08-13 |
| Util loader | `_default_util_loader` returns `[]` (line 387-391) — all MIF fields read `unavailable` | file read |
| Util substrate | `player_snap_count` table EXISTS in `nflverse_usage.db`; **no participation table exists locally** (route participation) | sqlite ro probe |
| Identity loader | `_default_identity_snapshot_loader` returns `[]` (line 490-493) | file read |
| Identity substrate | No governed universe sleeper→gsis snapshot series; only the TE 2018-2025 cohort snapshot (May). A sleeper↔gsis crosswalk exists via nflverse `ff_playerids` (`league_transactions._load_ff_playerids`; also `nflreadpy_qb_adapter`) | `ls app/data/identity/`; rg probes |
| Schedule loader | `"final" if home_score populated` (line 348-349) — the **known live finality-inference defect** the 2026-08-08 board names (nflverse publishes interim scores; B21 deliberately refuses this inference) | file read; AGENT_SYNC 08-08 §3 |
| Freshness config | `noop` ∈ `success_status` for `realized_outcome` (auxiliary tier), `dormant_ok: true` | `app/config/report_freshness.json:110-136` |

## 3. Mislead / verdict-by-the-back-door risks — the three remaining September traps

The 08-12 wiring closed trap #0 (undeclared frozen set → was `noop`, now exit 1). Remaining:

- **Trap A — empty identity bridge = healthy scorecard grading nothing.** Verified in
  `realized_outcome_scorer.score()`: with the identity loader returning `[]`, every prediction
  excludes as `identity_unresolved`, `tracking_rows`/`cohort_metrics` come out empty, and
  `run_scoring` stamps `status: ok`, writes the artifact, exits 0. **No zero-coverage guard
  exists anywhere in the path.** This is the same defect class as trap #0, one gate later.
- **Trap B — a week graded on partial outcomes presented as final.** The schedule loader's
  populated-score inference can mark an in-progress week `finalized` (interim scores are a
  documented nflverse behavior, B21 finding). A scorecard would then show realized-vs-expected
  deltas computed on incomplete games — false precision on the product's trust surface.
- **Trap C — in-season `noop` indistinguishable from health.** `report_freshness.json` treats
  any `noop` as success year-round. Off-season that is honest (`dormant_ok`). In-season, a
  scorer stuck on `week_not_finalized` for six weeks (e.g. broken schedule source) surfaces as
  a healthy fresh artifact. The marker DOES carry `noop_reason`; the freshness config just
  never reads it.

Overclaim check (No-Verdict Line): everything stays descriptive — `decision_supported=False`
recursively, marker carries execution state only (never model performance), no
verdict/recommendation language, no market comparison (divergence remains unvalidated
descriptive overlay). Nothing here bears on H2 QB rushing, which remains **UNDER TEST** with
no result.

## 4. Design questions for the cockpit (neutrally framed; lane positions in §6)

- **Q1 — Identity loader source.** The T2 bridge wants governed point-in-time identity
  snapshots; none exist for the universe. Options: (a) build snapshot dicts at scoring time
  from the pinned `ff_playerids` crosswalk (declared source+timestamp in the snapshot,
  request-time freshness caveat); (b) begin forward-capturing identity snapshots as a new
  governed store (compounding, but a new capture surface needing its own word); (c) some
  hybrid — (a) now with (b) as a named follow-up ticket.
- **Q2 — Finality evidence.** B21 alone can never emit `complete` (no terminal-status field
  exists upstream; the store records `result_observed_unverified`). Wiring the scorer strictly
  onto B21 semantics means it never grades. Options: (a) keep score-populated inference with a
  disclosed `finality_basis: observed_unverified` caveat field on the scorecard; (b)
  observed-score + stability window (grade only when every game's gameday is ≥ N days past,
  N pinned in config, basis disclosed); (c) require a David-declared per-week finality anchor
  (honest but manual every week); (d) defer the schedule-loader rewiring to a separate cycle
  and ship with the current inference plus disclosure. **Scope boundary question:** the 08-09
  board listed this consumer rewiring under OPEN FOR DAVID; the dispatch's "wire the loaders
  so a real finalized week actually grades predictions" plausibly covers it. The cockpit
  should agree on whether it is in-scope before the RED pins it.
- **Q3 — Util loader shape.** Snap share is derivable from `player_snap_count` (local,
  canonical). Route participation has **no local substrate** — options: per-field honest
  `unavailable` (ship snap-share only), or a new participation ingestion (a layer-1 stream
  needing its own word — NOT proposed here). `target_share_nfl` derivable from stat rows'
  team totals; confirm at RED time per the plan's own caveat (plan line 124).
- **Q4 — `noop` honesty.** Options: (a) leave config as-is (marker already distinguishes
  reasons; treat trap C as a freshness-system follow-up); (b) split statuses at the producer
  (e.g. in-season `week_not_finalized` beyond a bounded age becomes `failed`); (c) teach the
  freshness reader to read `noop_reason` + season windows (a `report_freshness` schema
  change — wider blast radius, its own contract tests). The dispatch says "make the noop
  semantics honest en route **if the spec requires it**" — the 2026-07-11 spec deliberately
  made noop healthy off-season; in-season semantics were never specified.
- **Q5 — Review scope.** The unreviewed 08-12 prediction-loader wiring is in this cycle's
  review scope (its author's handoff asked exactly that). The RED must pin its contracts too
  (declaration validation, 5-part join, `captured`-only filter, zero-row declaration failure).

## 5. Candidate falsification seeds (for the RED, whoever authors it)

1. Identity: empty bridge + non-empty predictions → scorecard/run must NOT terminate `ok`
   (zero-coverage guard: `graded == 0 ∧ predictions > 0` → failed or loud named noop).
2. Identity: conflicting same-date mappings → `conflict` excluded and counted, never resolved
   by input order (bridge already pins this; the loader must not defeat it).
3. Declaration: absent file · unreadable JSON · missing season · missing any of the four
   required fields · declared capture yielding zero rows → each a distinct named failure.
4. Util: snap-count rows present, participation absent → `route_participation_realized`
   `unavailable`, never imputed, never derived from snaps; wrong-season/week rows filtered.
5. Finality (per Q2 ruling): an interim-score game (populated score, same-day gameday) must
   not count toward `finalized` under the chosen rule; boundary cases at the stability-window
   edge pinned exactly (≥ vs >).
6. Freshness (per Q4 ruling): whichever semantics are chosen, a mutation test proving the
   unhealthy in-season state actually surfaces (no vacuous guard).
7. Numeric edges: non-finite `projection_2y` (loader already filters NULL; NaN/inf must fail
   loud per scorer `_finite`), duplicate sleeper_id in the frozen set, sleeper_id blank.
8. Marker/scorecard content scan: `decision_supported=False` recursively; no performance
   language in the marker; banned-language scan clean.
9. Read-only law: the scorer must never write to any source store (capture DBs opened
   `mode=ro`; temp outcome store auto-cleaned; `subprocess.run` forbidden seam intact).

## 6. Lane position (Claude, held as a principal — not a lock)

Cheapest honest increment consistent with the approval: **Q1(a)** crosswalk-built snapshots
with declared provenance + follow-up ticket for governed capture; **Q2(b)** observed-score +
pinned stability window with `finality_basis` disclosed on the scorecard (a real finalized
week grades within days, and no silent "final" claim ships — (a) alone repeats the defect the
board already names, (c) doesn't survive contact with a weekly cadence, (d) leaves the trap
armed); **Q3** snap-share now, route participation honestly `unavailable`, no new ingestion
stream off this cycle; **Q4(b)** producer-side split (narrowest blast radius; the freshness
reader stays dumb); **Q5** yes — one RED covering both increments. Codex may well break any
of these; that is what this round is for.

## 7. What this cycle does NOT do

No commit (gate paths only: Judge SHIP or David's word) · no push · no scheduler install ·
no live nflreadpy call as part of TDD (loaders stay injected/fixtured; the first live
finalized-week run remains the David-gated validation moment) · no DG-09 declaration
authored (David's decision; Claude writes the file when he rules) · no Studio contact ·
nothing touching the frozen wire pair (`b3247ec8…`/`fd924eb1…`, verified untouched today) or
the frozen Footballguys v26 pair.
