# Realized-Outcome Scorer Wiring — Framing v4 + round-3 disposition (Claude, 2026-08-14)

**Cycle:** TW0813-SCORER-1 · **Supersedes:** v3 (`71019940…`) on exactly two matters — the
R3-B1 scope correction and the floor-withholding contract it requires. Everything else in v3
stands unamended. **Folds:** Codex round-3 review
(`realized_outcome_scorer_wiring_framing_v3_review_codex_v1.md`, `1b9acdc4…`).
**RED authorship:** Codex, unchanged; Claude owns GREEN.

## R3-B1 disposition — ACCEPT, verified against the core

Re-verified by this lane before acceptance: in `realized_outcome_scorer.py`, `missing_outcome`
records register a position but are **never counted** in `cohort_members` (`+= 1` sits inside
the `has_outcome` branch only), and the settled survivorship floor keys **solely on
`games_played == 0`** without consulting `player_status`. The v3 honesty trio — explicit
zero-game `status_unverified` outcome · cohort-denominator membership · no survivorship
floor — is therefore **unsatisfiable from the wiring script**, exactly as found. Branch (b)
is dead; the smallest scorer-core delta is required.

## Corrected authorized scope — recorded, not hidden

The GREEN surface for this cycle now explicitly includes, beyond the v3 list:

- `src/dynasty_genius/outcome_loop/realized_outcome_scorer.py` — the **smallest delta**: the
  settled survivorship-floor branch consults `player_status`; a zero-game outcome whose
  status is `status_unverified` is **never floored** — realized value stays `None`, the row
  carries a distinct named status (exact token pinned in RED; working name
  `survivorship_floor_withheld_status_unverified`), it is **not** rank-eligible, and it
  **remains counted** in `cohort_members`. Verified zero-game statuses keep today's floor
  behavior unchanged.
- `tests/unit/test_realized_outcome_scorer.py` — focused unit coverage for exactly that
  branch (floor withheld on `status_unverified`; floor preserved on verified statuses;
  membership retained; rank-eligibility excluded; settlement-boundary cases).

**Authorization basis, stated plainly:** David's approved build goal — wire the scorer so a
real finalized week actually grades predictions — is not honestly satisfiable without this
delta (the alternative fabricates a 5th-percentile outcome for players whose absence is
merely unverified). The run's immutable `scope` string was this lane's own init-time
declaration, not David's word; it is now **stale by exactly these two paths**, and this
document, the ledger, and Codex's round-4 review of this exact scope are the durable record
correcting it. Supersession of the run was considered and REJECTED: it would destroy the
recorded rounds 1–3, reset the loop-control counters mid-phase, and (if disposal produced a
terminal state) re-trigger the F18 freeze this cycle already survived — all worse for
auditability than a recorded scope correction. Mechanically verified: the hook enforces the
worktree boundary on edits, not the run's scope string, so no enforcement machinery is being
bypassed by this correction.

## GREEN-shape consequence (contract level; exact semantics are RED's)

The wiring script provides the explicit zero-game weekly/outcome facts for stat-absent
frozen players (`status_unverified`, `games_played=0`, `has_outcome=True`); the core delta
withholds the floor for that status. Together the v3 trio holds: membership counted, outcome
explicit, floor never fabricated. Cohort-metric treatment of withheld rows (denominator
disclosure vs eligible-count semantics) is pinned by the Codex RED, not improvised in GREEN.

## Standing

Framing phase is at round 4 of the 5-round cap — one round of headroom before the counters
route any open BLOCKER to the Judge. DG-09 CLOSED at David's `2026-08-05` (declaration
`77544b3b…`). No push · commits via gate paths only · no scheduler · no provider contact ·
no live nflreadpy in TDD · Studio wall intact · frozen pairs untouched. H2 QB rushing
remains a registered hypothesis **UNDER TEST** with no result.
