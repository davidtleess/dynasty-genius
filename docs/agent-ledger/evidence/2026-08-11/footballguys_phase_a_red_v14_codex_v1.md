# Footballguys Phase A RED v14 — Codex v1

**Date:** 2026-08-11 ET  
**Layer:** 1 — ingest/persistence  
**Baseline GREEN:** `src/dynasty_genius/sources/footballguys_intake.py` SHA-256
`7d1090c27e8f7c3a87384315c47d02a8f900b183bfbe5663100b58d6169365b8`

## Authority and scope

The implementing lane accepted the sole adversarial finding against commit `e19d056` and
explicitly requested Codex-authored RED v14. The accepted rule closes the whole event-table
grammar: exactly six ordered segments, each matching its canonical column definition
token-for-token, and no table-constraint segment.

This act changes only the prospective contract plus evidence/ledger/wire. It authorizes no GREEN,
config, manifest, runtime, provider, scheduler, commit, push, capture, or Phase B/C/D work.

## Controls added

The v14 matrix rebuilds `event_sequence` with the real six columns and exercises:

1. the canonical six-segment definition as a positive control;
2. load-bearing top-level `CHECK(seq > 100)`;
3. named `CONSTRAINT seq_floor CHECK(seq > 100)`;
4. redundant top-level `UNIQUE(seq)`;
5. a noncanonical suffix on each non-`seq` column definition; and
6. canonical definitions in a noncanonical order.

Every negative requires `store_schema_unmigratable:semantics` from initialization and then proves
that `event_sequence` still contains zero rows. The matrix extends beyond the minimum extra-segment
examples because a six-segment-count-only implementation would otherwise satisfy those examples
while still accepting modified definitions; that would be a passes-broken-code RED.

Inherited v13 separately binds exact `seq`-column tokens, including its load-bearing suffix check.

## Binding census

Exact strict command, run twice:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -W error -m pytest -q --tb=no tests/contract/test_footballguys_phase_a_red.py
```

Both runs produced:

```text
425 collected = 9 failed + 416 passed, exit 1
```

The failures are exactly the nine v14 noncanonical tables: three extra constraints, five modified
non-`seq` definitions, and one order mutation. The v14 canonical positive and all inherited 415
contracts pass.

## Quality gates

- Ruff on the RED: clean.
- Python 3.14 compilation under `-W error`, with bytecode writing disabled: clean.
- No skip, skipif, or xfail markers/calls.
- `git diff --check`: clean.
- Baseline GREEN remains byte-identical at `7d1090c2…`.

## State

RED v14 is authored and intentionally failing. Nothing is committed or pushed. No capture,
provider contact, scheduler, or Phase B/C/D work opens. H2 QB rushing remains **UNDER TEST** with
no result and is unrelated.
