# Footballguys Phase A GREEN v8 adversarial review — Codex v1

**Date:** 2026-08-11 ET  
**Reviewed commit:** `7e39763afcf8449545f7ca6878c5f2d8d942276d`  
**Verdict:** **NOT CLEAR — five findings**  
**Layer:** 1 (ingest/persistence)

## 1. Pin and scope audit

The committed bytes reproduce the declared pins exactly:

- RED `tests/contract/test_footballguys_phase_a_red.py`:
  `8a31fd9472f9554a62db40b6b8f02a159a4007d7beac7703164bb8797f96898a`
- GREEN `src/dynasty_genius/sources/footballguys_intake.py`:
  `241d031dc4e36ee3f54500df8d6e9ad2bcd9fb208bdc5f062d0fc4b6c7ad8f4c`

The commit has parent `b346ac687fbaf340974a7a16d1792b0d87c6868b`, changes exactly the declared
three files, and reports `+573/-73`:

1. `docs/agent-ledger/2026-08-10.md`
2. `src/dynasty_genius/sources/footballguys_intake.py`
3. `tests/contract/test_footballguys_phase_a_red.py`

Current HEAD later advanced through evidence work, but `git diff 7e39763 --` over the RED and
GREEN paths is empty. This verdict binds the committed blobs above, not ambient untracked work.

## 2. Reproduced gates

- Cold strict RED:
  `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -W error -m pytest -q --tb=no tests/contract/test_footballguys_phase_a_red.py`
  → **340 passed, exit 0** in 17.71s.
- Full tracked suite with the standing cadence-RED exclusion:
  `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -m pytest -q --ignore=tests/contract/test_governed_cadence_inputs_red.py`
  → **5,573 passed / 12 skipped / 9 xfailed, exit 0** in 465.89s.
- `uvx ruff check src app` → clean.
- Cold `python -W error -m py_compile` of the GREEN module → exit 0.

These results reproduce the implementing lane's census. They do not falsify the findings below;
each finding uses a temporary isolated repository root and real SQLite files through the committed
GREEN.

## 3. Findings

### 1. CRITICAL — conflicting duplicate semantic-evidence identities can be laundered into Phase-C eligibility

`_migrate_semantics_store()` validates the semantic tables by column-name sets, but—apart from a
coarse event-ledger check—does not verify their primary-key/unique constraints. On load,
`semantic_state()` then folds attachment rows into a dictionary by `evidence_id` without detecting
duplicates (`footballguys_intake.py:2527-2538`). A restored exact-column
`semantic_attachments` table with no primary key is therefore accepted as governed; duplicate
identities collapse by row order.

Concrete probe:

1. Write the governed `redraft` assertion and its retained provider-authentic attachment.
2. Rebuild only `semantic_attachments` with the exact declared columns but no primary key.
3. Insert two rows with the same `evidence_id`: first an unsupported-provenance row, then the
   original valid row.
4. Re-run `initialize_database("semantics")` and `semantic_state(...)`.

Observed: initialization returned `wal`; the database contained **2 rows / 0 indexes** for the
same identity; the reducer returned `state=known`, `value=redraft`, and
`eligible_for_phase_c=True`. Reversing physical row order changes which duplicate wins. Conflicting
governed evidence must be an integrity failure, never last-row-wins eligibility.

Required boundary: validate every load-bearing PK/UNIQUE constraint by indexed column and reject
duplicate identities before any dictionary/reducer projection. Cover assertions, attachments,
evidence objects, and adjudications—not only the event ledger.

### 2. HIGH — the event uniqueness validator accepts a unique index on the wrong column

At `footballguys_intake.py:1414-1421`, the migration accepts **any** unique index reported by
`PRAGMA index_list(event_sequence)`. It never inspects `PRAGMA index_info` to prove a full,
non-partial unique constraint on `event_id`.

Concrete probe: create the exact expected event columns with `UNIQUE(subject_id)` and no event-id
constraint. `initialize_database("semantics")` accepted it. Two rows with `event_id='dup'` and
different subjects then committed successfully. The later reconciler detects an actual duplicate,
but the migration has already labelled a structurally invalid central-truth schema governed.

Required boundary: require the exact unique-key target (`event_id`), reject partial/expression or
wrong-column substitutes, and prove a duplicate `event_id` fails at SQLite insertion.

### 3. HIGH — reconciled event times are not canonical or comparable; the read model can raise

The central-row guard at `footballguys_intake.py:2824-2836` proves only that `event_at` is a
nonempty string. `_event_key()` (`2736-2742`) accepts both offset-aware and offset-naive ISO strings,
then `_flag_newer_attempts()` compares the resulting datetimes.

Concrete probe:

1. Complete one valid retained intake and then one failed intake, producing an acquisition event
   and a later attempt event.
2. Change the acquisition claim and its matching central record to the same offset-naive
   `2026-08-10T12:00:00`; leave the attempt's governed event offset-aware.
3. Call reconciliation and `read_model()`.

Observed: `_event_ledger_reconciled()` returned **`reconciled`**; `read_model()` raised bare
`TypeError: can't compare offset-naive and offset-aware datetimes`. An unparsable or future-but-
matching event can instead remove the acquisition order key and suppress the newest-attempt
overlay.

Required boundary: canonicalize and validate every event instant on write and read, including
timezone awareness and the applicable future-instant rule; validate sequence as an exact integer;
malformed persisted order facts must produce a named fail-closed state, never an exception or a
silently missing overlay.

### 4. HIGH — the claimed validate-before-mutate refusal changes rejected database bytes

The comments and RED describe a populated unreconcilable central ledger as byte-frozen, but
`initialize_database()` executes `PRAGMA journal_mode=WAL` at `footballguys_intake.py:1437-1446`
before `_migrate_semantics_store()` validates the schema.

Concrete probe: create a DELETE-mode `semantics.db` containing a populated bare
`event_sequence(seq)`. Before initialization it was 8,192 bytes with SHA-256
`44a2ec2b8c43491dec9aafd7a245746aae311a69424cfb38d52b021caf555e34`. Initialization correctly
raised `store_migration_unreconcilable:semantics`, but afterward the same-size file hashed
`5eedeef59cf7b91a99906e4257b1e976d0dd44817d9175faf8866d9d4c9fe516` and reported journal mode
`wal`.

Required boundary: perform the refusal-class schema/history validation through a non-mutating read
before WAL establishment, or explicitly narrow the byte-freeze promise and bind the exact allowed
pre-refusal mutation. The current prose, test claim, and syscall order disagree.

### 5. MEDIUM — the adjudication writer still leaks bare exceptions for malformed identity fields

`write_semantic_adjudication()` closes types for authority, provenance, and parents, but not for
`key`, `adjudication_id`, or `effective_assertion_id`. This leaves its supposedly total domain
boundary incomplete.

Concrete probes against an otherwise correctly shaped record:

- `key=[]` → bare `sqlite3.ProgrammingError` during parameter binding.
- `effective_assertion_id=[]` → bare `TypeError` during set membership.

Neither becomes a named `FootballguysIntakeError`, and both bypass the writer's advertised
presence/type refusal contract.

Required boundary: validate every adjudication identity/key field as nonempty text before relation
checks or SQLite calls; mutation tests must cover unhashable/wrong-type values for each field and
assert unchanged semantic state.

## 4. Review disposition

**NOT CLEAR.** The commit scope and published test censuses are accurate, and the new bounded
observe-open-reobserve tests pass. The five findings above remain outside that RED. Finding 1 can
turn conflicting persisted semantic evidence into a positive Phase-C eligibility result, so this
pin must remain unpushed and no first capture should run against it.

No RED/GREEN/config/runtime/manifest changes were made by this review. No provider contact,
capture, scheduler, Phase B/C/D work, commit, or push is authorized. H2 QB rushing remains
**UNDER TEST** with no result and is unrelated.
