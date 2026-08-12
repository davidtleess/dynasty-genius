From Codex (RED authoring lane) — Footballguys Phase A RED v17 authored

RED v17 is authored against the accepted review of `1e5492b`.

- `tests/contract/test_footballguys_phase_a_red.py`
- SHA-256 `00299c99798dbfd1c6bb582704b7b143fd3e70ae8bf6e45babf5d0d182ce4689`
- 5,500 lines / 213,411 bytes
- baseline GREEN remains byte-exact at `63c31c1870b674ec0212fc301a2f995d909051b54c8ecac5430adf457ea4e1bb`

Strict census: **472 collected = 13 failed + 459 passed, exit 1**. Exact split:

1. H1 **4F** — operational closed-grammar `CHECK` mutant on assertions, attachments, evidence
   objects, and adjudications. The evidence-object oracle explicitly rejects false `written`.
2. H2 **5F** — PK→UNIQUE, NOCASE, DESC, event-origin, and marker-origin mutations. Real
   `index_xinfo` proofs bind origin, partial/expression/key status, direction, collation, and order.
3. M3 **4F** — canonical/legacy marker bodies followed by `STRICT`/`WITHOUT ROWID`.

The 26 new cases include 13 passing anchors. Ruff, strict compile, and diff checks are clean;
there are no skip/xfail controls. Production is untouched.

Full record:
`docs/agent-ledger/evidence/2026-08-11/footballguys_phase_a_red_v17_codex_v1.md`.

PLEASE REPLY with the exact pre-repair census against this pin, then GREEN against it. Pair lands
only on David's word. No capture/provider/scheduler/Phase B/C/D. H2 QB rushing remains **UNDER
TEST** with no result and is unrelated.
