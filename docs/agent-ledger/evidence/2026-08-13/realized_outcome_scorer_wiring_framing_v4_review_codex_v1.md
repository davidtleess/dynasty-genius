# Realized-Outcome Scorer Wiring — Codex Framing v4 Review

**Cycle:** TW0813-SCORER-1 · **Date:** 2026-08-14 · **Lane:** Codex review  
**Reviewed artifact:** `realized_outcome_scorer_wiring_framing_claude_v4.md`  
**Reviewed SHA-256:** `77e92aed9daf0c6e6f3c31e91bd4aaf12b4835a5b6650b709e376c516a5a33df`  
**Verdict:** **CLEAR — no BLOCKER, WARN, or STYLE finding. Codex proceeds to RED.**

## Enumerated checks

1. **R3-B1 executable proof:** re-read the pure scorer. A `missing_outcome` row does not
   increment `cohort_members`; an explicit zero-game OutcomeRow does increment it and, today,
   takes the settled floor solely on `games_played == 0`. V4 correctly declares branch (b)
   dead and requires the core delta.
2. **Corrected scope:** v4 names exactly the two previously omitted paths:
   `src/dynasty_genius/outcome_loop/realized_outcome_scorer.py` and
   `tests/unit/test_realized_outcome_scorer.py`. The current user request explicitly asks for
   RED coverage of this core delta, and the relayed David-approved goal is the real finalized-
   week scorer build, not Claude's narrower init-time scope string. The correction adds no
   provider, ingestion stream, scheduler, declaration authorship, commit, or push authority.
3. **Core semantics pinned for RED:** exact output token
   `survivorship_floor_withheld_status_unverified`; realized value remains `None`; row stays in
   cohort membership; row is not rank-eligible; verified zero-game statuses keep the existing
   floor. Boundary coverage is week 33 versus settlement week 34.
4. **Denominator semantics:** the withheld row counts in frozen/outcome/cohort membership but
   not rank-eligible counts. The RED will require separately named declared, eligible,
   resolved, outcome-present, and rank-eligible denominators rather than reinterpret the
   scorer's legacy `eligible_count` field silently.
5. **V3 standing checks:** SHA and declaration pin held; read-only SQL reproduced the declared
   581 model-supported joinable universe (501 Engine-B captured + 80 Engine-A incomplete);
   the declared loader returns 501 score-eligible rows and refuses undeclared 2027.
6. **Substrate boundaries:** `ff_opportunity` remains consumer-banned and realized WOPR remains
   out; `player_snap_count.offense_pct` is the sole realized-util source this cycle; all other
   prediction-time model-input fields remain explicit `unavailable` when no governed realized
   source exists.
7. **Identity/finality/health:** the canonical pinned ff-playerids adapter and provenance rules
   stand; finality remains an injected evidence interface with provider choice David-gated;
   nonfinal age is strict `>14`, `==14` remains healthy noop, and absent/unparseable target
   gamedays fail loud on scheduled and explicit paths.
8. **No-Verdict/read-only:** `decision_supported=False` remains recursive; source databases
   stay URI `mode=ro`; temp outcomes remain ephemeral; git/subprocess prohibition remains.

## RED authorship

Codex holds RED. The contract will cover v3's consolidated GREEN list plus the exact v4
status-sensitive floor branch. Claude remains GREEN. CLEAR creates no commit or push authority.
