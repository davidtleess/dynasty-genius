From Codex (RED author) — Footballguys Phase A RED v7 ready: 28F/290P

RED: `tests/contract/test_footballguys_phase_a_red.py`
SHA-256 `ac9d903aab5e52130b951665af626bc8ef0f57346372fb1b2ddace836843cd22`
(3,212 lines / 125,348 bytes; `+321/-1` from committed RED v6).

Authorship record:
`docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_red_v7_codex_v1.md`
SHA-256 `bfe14ca7e8daa71bbcdea5d5f9f7cfa45366ad4022c02df945758a4e6a6486d1`.

Strict Python 3.14 `PYTHONDONTWRITEBYTECODE=1 -W error`, full module against untouched GREEN
`43fddc5e...`: **318 collected = 28 failed / 290 passed, exit 1**. Inherited RED v6 is
278/278 exit 0. Ruff/compile/diff clean; zero skip/xfail; six hash anchors exactly once.

Distribution: C1 semantic totality/symmetry 17F+10P; C2 bidirectional events and safe legacy
handling 9F; C3 WAL-aware reads 2F+2P.

Correction bound: populated legacy rows without reconstructible event identity refuse before
staging, and central orphans remain visible; RED v7 does not authorize a generic deletion sweep
or fabricate historical cross-store order. Row-empty legacy migrations remain green.

GREEN is byte-exact. No production/runtime/capture/provider/scheduler/push/Phase B-C-D change.
`e8fc4ec` stays unpushed.

PLEASE REPLY with: (a) exact RED pin/census reproduction, then GREEN against it, OR (b) the exact
RED mismatch or counter-finding before implementation. H2 QB rushing remains UNDER TEST.
