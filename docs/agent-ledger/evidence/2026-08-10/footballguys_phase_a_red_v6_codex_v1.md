# Footballguys Phase A RED v6 — Codex authorship record

## Authority and scope

Claude accepted all five findings from the committed `21cd11d` adversarial review, zero contested,
and explicitly requested Codex-authored RED v6. This act changes the executable contract only:

- RED: `tests/contract/test_footballguys_phase_a_red.py`
- SHA-256: `a5847de038524155c13cc89351414b413846f62703c209a502e34f208b01b59c`
- Size: 2,892 lines / 112,284 bytes
- Delta from committed RED v5: `+414/-1`
- Reviewed GREEN remains untouched at
  `68581fb37179a26e5f98e28a6660c31ebe43e60273b9c62c67ae683407bf9374`.

No production/config/runtime/provider/scheduler/board/push mutation is part of this act.

Source review:
`docs/agent-ledger/evidence/2026-08-10/footballguys_phase_a_green_21cd11d_review_codex_v1.md`
(`a6d1d9747016e17802ba9a8f02ad6caf4052fe91c4bfbe144ef436a9a9fff56a`).

## New contract surface

RED v6 adds 29 collected controls: 28 negative controls fail against the untouched GREEN and one
positive boolean-state control passes.

### C1 — common semantics/event store before staging

- non-SQLite common store + valid archive: named domain refusal before staging;
- readable but unmigratable semantic schema + valid archive: exact
  `store_schema_unmigratable:semantics` refusal;
- both assert zero canonical objects, zero real acquisitions, zero attempts, and zero staging
  residue.

These tests follow the real valid-archive path. The reviewed GREEN leaves a paid object on the
non-SQLite case and commits through the wrong-schema case.

### C2 — total semantic schema, writer and restored-state load

- writer rejects non-boolean `active`, empty assertion/key/evidence ids, unsupported retention,
  and non-bytes evidence before any mutation;
- explicit boolean `False` is the positive control: durable, inactive, and reducer-unknown;
- restored malformed attachment time, active scalar, and assertion id fail closed;
- non-BLOB evidence never reaches `len()`/hash as a Python type error;
- adjudication parents must decode to a JSON list of nonempty strings; malformed JSON, JSON object,
  and mixed-type list all reduce to unknown without raising.

### H3 — attempts relation participates in row-9 unreadability

- missing attempts table and wrong-column table both render the exact literal row 9;
- an inactive legacy counterpart with no attempts relation cannot be masked by a healthy retained
  acquisition;
- inherited RED v5 retains the whole-file non-SQLite cases.

### H4 — identity-bound central event records

- central `event_sequence` records are required to carry `event_id`, `event_type`, `store_name`,
  `subject_id`, `event_at`, and unique sequence;
- acquisition claims carry `event_id`; attempts carry both stable `attempt_id` and `event_id`;
- positive mapping proves acquisition/attempt type, store, subject, instant, and sequence bindings;
- deleting the central mapping, changing the store binding, or skewing a per-store sequence claim
  all fail closed rather than selecting copy.

The exact schema is deliberately pinned: an integer allocator cannot satisfy a contract that calls
the central table a governed event ledger.

### H5 — real inactive lookup under valid input

- both active modes × legacy/current inactive-store shapes;
- every case uses a valid archive, reaches the real lookup, and fingerprints main/WAL membership,
  size, and SHA before/after;
- only SHM residue is excluded from the comparison, matching the frozen framing contract;
- the main-only WAL-mode shape catches the reviewed GREEN's creation of a zero-byte WAL.

## Failing census against untouched `21cd11d` GREEN

Strict command: Python 3.14, `PYTHONDONTWRITEBYTECODE=1`, `-W error`, `pytest -q --tb=no`.

- **278 collected = 28 failed / 250 passed; process exit 1.**
- Inherited RED v5 alone: **249 passed / 29 deselected; process exit 0.**
- The 29 v6 cases are exactly **28 failed / 1 passed**.

Failure distribution:

- C1: 2;
- C2: 15 negative failures + 1 positive pass;
- H3: 3;
- H4: 4;
- H5: 4.

Representative real-boundary failure identities were rerun with short trace: paid-object residue;
bare `TypeError` on non-BLOB evidence; healthy current state over missing attempts; central schema
containing only `seq`; and four zero-byte-WAL creation failures.

## Quality and anti-shadow checks

- Ruff: clean.
- `py_compile` under `-W error`: pass.
- `git diff --check`: pass.
- skip/xfail/skipif count: zero.
- all six independent known-answer hashes remain present exactly once.
- RED v6 header names v6 and the `21cd11d` boundary.
- GREEN hash rechecked after RED authorship: unchanged at `68581fb3...`.
- The binding pre-RED full-suite baseline remains **5,482 passed / 12 skipped / 9 xfailed**, with
  only the standing untracked cadence RED excluded. The full suite is expected to turn red now
  because these 28 contract failures are intentionally executable.

## Disposition

RED v6 is uncommitted at the pin above. Claude reproduces the pin/census, repairs GREEN against it,
and the pair travels together in one separately reviewed act only on David's word. `21cd11d` stays
unpushed; no first capture, provider contact, scheduler, push, or Phase B/C/D opens.

H2 QB rushing remains **UNDER TEST** with no result and is unrelated.
