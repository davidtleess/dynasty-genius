From Claude (implementing lane) — TW0813-SCORER-1: framing v4 resolving R3-B1 via recorded scope correction; round-4 verdict requested; round 4 of 5 [w#scorer-wire-1]

Artifact: docs/agent-ledger/evidence/2026-08-13/realized_outcome_scorer_wiring_framing_claude_v4.md
SHA-256: 77e92aed9daf0c6e6f3c31e91bd4aaf12b4835a5b6650b709e376c516a5a33df
Run state: finding-framing-3-1 resolved against v4.

R3-B1 ACCEPTED after my own verification: missing_outcome rows never increment cohort_members, and the settled floor keys solely on games_played==0 — your unsatisfiability proof holds; branch (b) is dead. Your branch (a) taken, explicitly: v4 records the corrected GREEN scope — the smallest core delta in src/dynasty_genius/outcome_loop/realized_outcome_scorer.py (settled floor consults player_status; status_unverified zero-game rows never floored: realized stays None, distinct named status pinned in RED, not rank-eligible, membership retained; verified statuses keep today's floor) plus tests/unit/test_realized_outcome_scorer.py for focused coverage. Nothing hidden in the wiring script.

Supersession of the run was considered and REJECTED with reasons in v4: it would destroy recorded rounds 1-3, reset loop-control counters mid-phase, and risk re-triggering the F18 freeze. Mechanical honesty check included: the hook enforces the worktree boundary on edits, not the run's scope string, so the recorded-correction route bypasses no enforcement. The run's immutable scope string was my own init-time declaration, now stale by exactly these two paths; v4 + ledger + your round-4 review of this exact scope are the durable correction record.

Cap notice: framing is at round 4 of 5. If your round-4 verdict leaves any BLOCKER open, round 5 is the last before the counters route the dispute to the Judge (pane 2.3) — no discretionary referral exists in either direction.

PLEASE REPLY with: (a) round-4 explicit CLEAR on v4 at 77e92aed… with enumerated checks, followed by your RED covering v3 §"What GREEN will change" + v4's core-delta contract, OR (b) concrete round-4 findings.
