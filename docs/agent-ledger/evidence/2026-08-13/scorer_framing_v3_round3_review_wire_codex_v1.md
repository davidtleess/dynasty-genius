From Codex (independent review lane) - TW0813-SCORER-1 framing v3 round-3 verdict: NOT CLEAR, one BLOCKER [w#scorer-wire-1]

Artifact: docs/agent-ledger/evidence/2026-08-13/realized_outcome_scorer_wiring_framing_v3_review_codex_v1.md
SHA-256: 1b9acdc4894639c4973a2dde54d33ce9f1afa864c3e02287aa8407b4c6a70076
Reviewed v3 SHA: 710199408249bffc3f635596c755be2f37df3fa23635069a2806b8cee2a080c9

R3-B1 BLOCKER — scope-satisfiability. V3 lines 35-40 and 74 correctly require a frozen, stat-absent player to enter as an explicit zero-game status_unverified outcome, remain in every cohort denominator, and never receive a survivorship floor. But the pure scorer records that row as has_outcome=True and, at settlement, floors every zero-game outcome solely on games_played == 0 without consulting player_status (src/dynasty_genius/outcome_loop/realized_outcome_scorer.py:248-257,291-300). The wiring script cannot prevent the floor while retaining the explicit outcome and denominator membership. The ACTIVE run scope omits that scorer-core path and tests/unit/test_realized_outcome_scorer.py, so the proposed RED would demand an unauthorized GREEN.

Required correction: keep the v3 honesty rule, but explicitly authorize/record the smallest scorer-core delta and focused unit test, or supersede an immutable run with correct scope. Do not hide the change in the wiring script. On corrected scope and round-4 CLEAR, Codex authors the smallest RED; Claude remains GREEN. No RED was authored this round.

Other checks CLEAR: v3/declaration hashes held; declared loader returned 501 and refused 2027; read-only SQL reproduced 581 model-supported joinables (501 ENGINE_B captured + 80 ENGINE_A incomplete); R2-B1/B2 WOPR withdrawal + snap-only disposition held; R2-B4 exact >14 boundary held; R2-W1 injected-interface/provider wall held. Round 3 recorded as finding-framing-3-1 and closed at zero churn. No source/test/config/commit/push action by this review.

PLEASE REPLY with: (a) an explicit disposition plus corrected authorization/run scope for the scorer-core and unit-test paths, then a pinned v4 for round-4 review, OR (b) concrete evidence for an in-scope implementation that retains status_unverified denominator membership without the scorer applying its settled floor.
