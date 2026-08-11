# Footballguys Phase A RED v8 — Codex authorship record

Date: 2026-08-10  
Layer: 1 — intake/persistence  
Authority: Claude accepted all four `c183c11` GREEN-review findings, zero contested, and
explicitly requested Codex-authored RED v8.

## Pin

- Contract: `tests/contract/test_footballguys_phase_a_red.py`
- SHA-256: `8a31fd9472f9554a62db40b6b8f02a159a4007d7beac7703164bb8797f96898a`
- Size: 3,580 lines / 139,756 bytes
- Delta from committed RED v7: `+369/-1`
- Reviewed GREEN remains untouched at
  `657873570fb35beaecf5cc44ee7bf18a7e6917c9b4cd94028874ec21e329b607`.

## Binding census

Exact strict command:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -W error -m pytest -q --tb=no \
  tests/contract/test_footballguys_phase_a_red.py
```

Result against untouched GREEN:

```text
340 collected = 17 failed / 323 passed, process exit 1
```

Inherited RED v7 alone remains:

```text
318 passed / 22 deselected, process exit 0
```

RED v8 contributes 22 cases: 17 negative failures and five positive/adjacent controls.

## C1 — central event ledger is governed in its own right

The new controls bind all of the accepted central-ledger repair, rather than merely checking
store-side claims:

- a populated historical `event_sequence(seq)` refuses
  `store_migration_unreconcilable:semantics` before any migration, staging, or publication;
- a row-empty historical allocator migrates only by a table rebuild that creates a real SQLite
  uniqueness constraint on `event_id`;
- an exact-column table without that uniqueness refuses as unmigratable before a later intake;
- duplicated central IDs are also detected on a read-only load before dictionary collapse;
- every central row has closed, non-null identity, event-type, store, subject, and instant fields;
- an unreadable central ledger fails closed as framing row 9 even when there are zero acquisition
  or attempt claims to compare.

Failure/control split: seven failing and four passing. The four passing malformed-row cases are
positive evidence that the reviewed GREEN already fails closed for some central orphans; the RED
isolates the two ignored type shapes, duplicate-collapse path, schema-constraint gap, unsafe
migration, and zero-claim unreadable path instead of treating all malformed rows as one outcome.

## C2 — any unreadable counterpart relation blocks before provider bytes

Four mode-by-relation cases install a valid SQLite counterpart whose `acquisitions` or `attempts`
relation has the wrong shape. Both active retention modes are covered. Intake must refuse by the
exact relation name:

```text
store_unreadable:<store>.<relation>
```

The contract asserts no staging call, no canonical object, and no raw provider-bearing staging
residue. The row-9 read behavior remains inherited; this new boundary prevents a writer from
publishing first and reporting the already-known corruption later. All four cases fail against
the reviewed GREEN.

## H3 — semantic vocabulary type checks precede set membership

Five controls supply unhashable list values for assertion claim, attachment provenance and
retention, and adjudication authority and provenance. Every present-but-wrong-type value must
produce its named domain refusal and leave semantic state unchanged; no `TypeError` or false
`missing_field` diagnosis may escape.

Two membership cases leak raw `TypeError`, two adjudication cases misclassify a present value as
missing, and the retention companion already passes. This split prevents an implementation from
making the whole writer red while leaving the exact pre-membership type boundary untested.

## H4 — SQLite reader selection is stable across open

Two deterministic controls require one production file-set observer used by the real read path:

1. A valid committed WAL that drops `attempts` appears immediately after the first observation.
   The reader must detect the post-open mismatch, close, retry in WAL-aware mode, observe the
   committed state, and render row 9.
2. The observed file set alternates forever. Retries must be bounded (the contract allows no more
   than 64 observer calls for the whole read) and the stream must fail closed as row 9.

The observer is patched only to make the real check/use window deterministic. The archive/store
fixtures and SQLite connections remain production implementations; no verdict is asserted from a
mock classifier alone. Both controls fail because the reviewed GREEN has no observe-open-
reobserve boundary.

## Anti-shadow and hygiene checks

- Strict inherited suite: 318/318, exit 0.
- Ruff on the touched test: clean.
- Cold Python 3.14 `py_compile -W error`: clean.
- `git diff --check`: clean.
- Runtime skip/skipif/xfail markers: zero (the only textual `skip` hits are historical prose).
- Every negative is paired with a physical or state consequence: unchanged pre-migration bytes,
  a real SQLite unique constraint, zero prewrite residue, unchanged semantic rows, row-9 copy, or
  a bounded observer count.
- No GREEN, runtime store, manifest, scheduler, provider, or downstream file was changed.

## Gate

RED v8 is uncommitted. Claude must reproduce this exact pin and 17F/323P census before repairing
GREEN. RED and GREEN travel together only on David's later landing word. `c183c11` remains
unpushed; no first capture, provider contact, scheduler, runtime-store mutation, push, or Phase
B/C/D work opens. H2 QB rushing remains **UNDER TEST** with no result and is unrelated.
