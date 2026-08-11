From Codex (RED-authoring lane) — Footballguys Phase A RED v9 authored and intentionally failing

RED: `tests/contract/test_footballguys_phase_a_red.py`
SHA-256 `54eccc7326cba73d2e6d662c16b239387344dfcd0a3b1e170bc38ebaecf79332`
Size: 3,973 lines / 155,087 bytes.

Record:
`docs/agent-ledger/evidence/2026-08-11/footballguys_phase_a_red_v9_codex_v1.md`
SHA-256 `7db6925f7f008e74720b8b1039d812845962272b46195952f1637f7ad2d0d05a`

BASELINE GREEN remains byte-untouched at `241d031dc4e36ee3f54500df8d6e9ad2bcd9fb208bdc5f062d0fc4b6c7ad8f4c`.

STRICT CENSUS against that GREEN: **371 collected = 31 failed + 340 passed, exit 1** under
`PYTHONDONTWRITEBYTECODE=1` and `-W error`. Failure identities reproduce on a second run.

BREAKDOWN:
- C1 = 16: for all four semantic identity tables, missing/wrong-column/partial constraints refuse;
  restored duplicates fail before projection with `semantic_identity_duplicate:<table>`.
- H2 = 2: wrong-column and partial event_id unique substitutes refuse; inherited canonical
  insertion positive remains green.
- H3 = 6: naive/fractional/future/malformed persisted event instants, TEXT event sequence, and a
  fractional writer clock all bind named fail-closed behavior.
- H4 = 1: chosen option is NON-MUTATING prevalidation before any write-capable connection or WAL
  pragma; DELETE-mode unreconcilable store remains byte-frozen.
- H5 = 6: unhashable/wrong-type adjudication_id, key, and effective_assertion_id reach exact named
  refusals with row count and effective semantic state unchanged.

RED QUALITY: all inherited 340 green; no skip/xfail decorators; Ruff clean; cold strict compile
clean; `git diff --check` clean. No GREEN/config/manifest/runtime/provider/scheduler changes. No
commit/push/capture. Phase B/C/D stay closed. H2 QB rushing remains UNDER TEST with no result.

PLEASE REPRODUCE the RED pin and 31F/340P census before GREEN. Pair lands only on David's word.
