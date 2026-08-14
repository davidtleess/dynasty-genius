# Realized-Outcome Scorer Wiring — Codex Framing v3 Review

**Cycle:** TW0813-SCORER-1 · **Date:** 2026-08-14 · **Lane:** Codex review  
**Reviewed artifact:** `realized_outcome_scorer_wiring_framing_claude_v3.md`  
**Reviewed SHA-256:** `710199408249bffc3f635596c755be2f37df3fa23635069a2806b8cee2a080c9`  
**Verdict:** **NOT CLEAR — one BLOCKER. No RED authored.**

V3 correctly integrates R2-B1, R2-B2, R2-B4, and R2-W1. It also states the right
honesty rule for R2-B3, but that rule is not executable inside the active run's authorized
scope.

## R3-B1 — BLOCKER: the `status_unverified` contract requires an unauthorized scorer-core change

V3 lines 35–40 requires an explicit zero-game `status_unverified` OutcomeRow to remain in
the cohort while never receiving a survivorship floor. Its consolidated GREEN list repeats
that contract at line 74.

The pure scorer currently does the opposite. A seeded OutcomeRow enters as
`has_outcome=True` and carries `player_status` (`realized_outcome_scorer.py:248-257`), but at
the settled horizon every such zero-game row takes the survivorship-floor branch solely on
`games_played == 0` (`:291-300`). That branch never consults `player_status`. The wiring
script cannot prevent the substitution while simultaneously supplying the explicit outcome
and retaining the frozen player in the cohort denominator.

The active autonomy run authorizes `scripts/run_realized_outcome_scoring.py`, its existing
contract file, a new RED under `tests/contract/`, and ledger/evidence paths. It does **not**
authorize `src/dynasty_genius/outcome_loop/realized_outcome_scorer.py` or its unit tests.
Therefore the proposed RED would knowingly demand a GREEN outside the run scope, violating
the operating-loop no-scope-expansion gate.

**Required correction:** retain v3's honesty rule, but explicitly obtain/record authority for
the smallest scorer-core delta and its focused unit test (recommended paths:
`src/dynasty_genius/outcome_loop/realized_outcome_scorer.py` and
`tests/unit/test_realized_outcome_scorer.py`) before asking Codex to author the RED. If the
active run's scope is immutable, supersede it with a correctly scoped run rather than hiding
the core change in the wiring script.

## Checks and integration results

- Matched v3 SHA `71019940…` and frozen declaration SHA `77544b3b…`; read the declaration's
  verbatim David ruling (`2026-08-05`).
- Re-ran the declared loader: `_default_prediction_loader(2026, 1)` returns 501 rows; season
  2027 raises `FrozenPredictionSetUndeclared`.
- Re-ran read-only SQL for `2026-08-05`: 12,209 snapshot rows total; the five-key joinable,
  model-supported universe is exactly 581 (`ENGINE_B/captured=501` plus
  `ENGINE_A/capture_incomplete=80`). V3's denominator correction holds.
- R2-B1/B2: re-read the symbol-level `ff_opportunity` consumer ban and executable Engine-B
  formula. V3 correctly removes realized WOPR and keeps snap-share only; no new finding.
- R2-B4: verified `SCHEDULED_TARGET_MAX_AGE_DAYS = 14` is shipped and the v3 boundary is
  strict `>14`, with `==14` healthy and indeterminate gamedays loud on both invocation paths;
  no new finding.
- R2-W1: v3 limits this cycle to an injected finality-evidence interface and leaves provider
  choice David-gated; no new finding.
- Inspected the current wiring diff, scorer core, settled survivorship unit test, and active
  run status. The existing unit contract proves a verified `departed` zero-game row should
  still receive the floor; v3 needs a new status-sensitive branch, not removal of the floor.

## RED authorship

Codex continues to hold RED authorship. RED is intentionally not authored while R3-B1 is
open: doing so would freeze an unsatisfiable in-scope contract. On a corrected scope and
round-4 CLEAR, Codex will author the smallest failing contract; Claude remains GREEN.
