From Codex (independent review / RED lane) — TW0813-SCORER-1: framing v4 CLEAR; RED v1 frozen and ready for adversarial review then GREEN [w#scorer-wire-1]

Framing review: docs/agent-ledger/evidence/2026-08-13/realized_outcome_scorer_wiring_framing_v4_review_codex_v1.md — SHA-256 45112e032970418c83a6dda09da16716876ed901d5d5728747057db2baa32a0a. Explicit CLEAR on v4 77e92aed9daf0c6e6f3c31e91bd4aaf12b4835a5b6650b709e376c516a5a33df after eight enumerated checks; round 4 reviewer-clear recorded and closed.

RED artifacts:
- tests/contract/test_realized_outcome_scorer_wiring_red.py — SHA-256 723545885e652a3cbcc004b04a398f6904022024a2eece4841bddd6af63a0137
- tests/unit/test_realized_outcome_scorer.py — SHA-256 b7b0d85d3e49545df8222329b37782b175a0970404f18346656f736da10cc7f9 (+35 focused lines)
- docs/agent-ledger/evidence/2026-08-13/realized_outcome_scorer_wiring_red_codex_v1.md — SHA-256 ba45dd1cb6a3232d8cc4c83289bcfa93a1190a1c9845b2fd33ddd4f91a269ae6

RED proof: targeted 27 failed / 3 positive-control passed / 9 deselected; combined 39 collected, no errors. Existing scorer unit baseline excluding the new row: 9 passed (two known SciPy warnings). Existing CLI contract: 10 passed. py_compile, touched Ruff, and diff-check pass. No product source edited by Codex.

Frozen contract headline: default predictions return dynamic {rows,coverage} from declaration-relative five-key joinables (production 581, never hardcoded); malformed declaration/utilization fail named; canonical ff-playerids reuse pins timestamp/SHA/version/duplicates and preserves frozen dg_player_id; player_snap_count maps PFR→GSIS and emits validated snap only; frozen stat-absent players get explicit status_unverified + unavailable weekly facts; nonfinal day 14 noop/day 15 failed on both paths; mixed malformed gamedays fail loud; score-derived default schedule never certifies finality; coverage propagates to result/scorecard/marker and zero-graded fails; settled status_unverified retains membership but gets no floor, exact status survivorship_floor_withheld_status_unverified; verified departures keep today's floor; source DBs remain URI-read-only; ff_opportunity remains absent.

Per 02, review the RED adversarially before GREEN. Do not weaken/delete a row to make GREEN; route any contract defect back with evidence. No commit or push authority.

PLEASE REPLY with: (a) explicit RED CLEAR after enumerating the contract checks you ran, then implement GREEN and return the pinned diff plus focused/full verification for Codex review, OR (b) concrete RED findings naming the test, violated framing clause, and smallest correction.
