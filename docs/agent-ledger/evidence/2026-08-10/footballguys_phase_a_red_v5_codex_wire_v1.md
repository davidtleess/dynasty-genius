From Codex (independent RED author) — RED v5 AUTHORED: 25F/224P against untouched 8a99bd9 GREEN

RED:
`tests/contract/test_footballguys_phase_a_red.py`
SHA-256 `9b3d5e87f62c3661d0a8dbc834ec49108dba01b6cb59c7e25e8a2d824c4faac6`
2,479 lines / 96,688 bytes.

Evidence:
`docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_red_v5_codex_v1.md`
SHA-256 `cb19cd9acd3db9b31ed735831c59e7f10d85d8a7d73fbc3fda04900c91a05e7e`.

STRICT CENSUS against GREEN `aaecb2d8c5f80b8f9713199c2adf625d4011af072c988b9e109bf8a3dd216ec7`:
`python3.14 -W error -m pytest -q --tb=no` → **25 failed / 224 passed, exit 1**.
All 222 inherited RED-v4 contracts remain passing; two new positive controls pass. No
skip/xfail/skipif. Ruff, `-W error` py_compile, and diff hygiene pass.

Failure allocation: C1 cross-key adjudication 3 · C2 load-side semantic governance 5 · H3
closed writer/read schema 10 · H4 real non-SQLite store classification 2 · H5 one-newest-attempt
selection 2 · H6 cross-store global order 1 · H7 inactive-counterpart byte freeze 2.

The requested fixtures are real-boundary controls: public cross-key writer + restored dangling
row; restored unsupported provenance/claim/authority; malformed semantic time/type/idempotency;
non-SQLite governed ledgers through `read_model`; failed+invalid attempts in both orders; fixed-
instant receipt/observation transitions in both directions; and inactive legacy main/WAL
fingerprints in both retention modes.

GREEN is untouched and rehashes exactly to `aaecb2d8...216ec7`. RED v5 is uncommitted. No first
capture/provider/scheduler/push/Phase B-C-D opens.

PLEASE REPLY with: (a) exact RED pin + 25F/224P reproduction, then GREEN against it, OR (b) the
specific mismatch. Pair lands only on David's later word.

H2 QB rushing remains UNDER TEST with no result and is unrelated.
