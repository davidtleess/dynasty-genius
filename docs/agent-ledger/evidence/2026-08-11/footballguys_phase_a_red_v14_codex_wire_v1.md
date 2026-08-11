From Codex (RED author) — Footballguys Phase A RED v14 authored and intentionally failing

RED: `tests/contract/test_footballguys_phase_a_red.py`
SHA-256: `9e5e12c2f43f988bb3e819b4377be54b4c4886e6ace49a944962a47cce24e0e8`
Size: 4,724 lines / 184,345 bytes.

Exact strict census, reproduced twice against unchanged GREEN `7d1090c2…`:
**425 collected = 9 failed + 416 passed, exit 1**.

The v14 canonical six-segment table and all inherited 415 controls pass. The failures are exactly:
- three extra table segments: load-bearing CHECK, named CONSTRAINT, redundant UNIQUE(seq);
- one noncanonical suffix on each of the five non-seq column definitions; and
- canonical definitions in the wrong order.

Every negative requires `store_schema_unmigratable:semantics` at initialization and then proves
zero event rows. I expanded beyond the minimum extra-segment examples because a six-segment-count-
only implementation would otherwise pass the RED while violating the accepted token-for-token
definition rule.

Ruff clean; Python 3.14 `-W error` compile clean; no skip/xfail; diff check clean. GREEN remains
byte-identical at `7d1090c27e8f7c3a87384315c47d02a8f900b183bfbe5663100b58d6169365b8`.

Evidence:
`docs/agent-ledger/evidence/2026-08-11/footballguys_phase_a_red_v14_codex_v1.md`
SHA-256 `e0e52740063036a9d845aa48d430b9eedd959fe48f3cf5f60a0f5030252ad85f`.

Nothing committed or pushed; no capture/provider/scheduler/Phase B-C-D. H2 QB rushing remains
UNDER TEST with no result and is unrelated.

PLEASE REPLY with the exact pre-repair reproduction before GREEN begins.
