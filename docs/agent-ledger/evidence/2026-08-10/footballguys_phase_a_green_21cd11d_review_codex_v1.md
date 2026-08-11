# Footballguys Phase A GREEN review — committed pin `21cd11d` (Codex)

**Verdict: NOT CLEAR — 2 Critical / 3 High.** The post-commit scope and submitted pins are exact,
and every declared gate reproduces. The blockers are behavioral sibling boundaries reached through
the committed driver against disposable filesystem/SQLite roots. No provider payload, production
runtime store, scheduler, capture, or downstream phase was touched.

## Committed boundary

- Commit: `21cd11d30395c679e956ca107c3f5073781cda3c`; parent
  `d7d5bb162e84f84cc6107e87d7fd30a7154ae66a`.
- Exact diff: three declared paths, `+602/-43`:
  - ledger `+7/-0`;
  - GREEN `+153/-42`;
  - RED v5 `+442/-1`.
- RED blob and worktree pin:
  `9b3d5e87f62c3661d0a8dbc834ec49108dba01b6cb59c7e25e8a2d824c4faac6`.
- GREEN blob and worktree pin:
  `68581fb37179a26e5f98e28a6660c31ebe43e60273b9c62c67ae683407bf9374`.
- The later HEAD commit changes documentation only; both reviewed files remain byte-identical to
  `21cd11d`. `git diff --check` on the reviewed commit is clean.

## Numbered findings

### 1. Critical — the common semantics/event store is first validated after raw publication

`_prepare_stores()` prepares only the selected acquisition database
([GREEN line 1809](../../../../src/dynasty_genius/sources/footballguys_intake.py#L1809)). A fresh
archive is then linked and made durable at lines 1721–1758. Only during receipt commit does
`_allocate_event_seq()` initialize/use `semantics.db` at lines 1891 and 1920–1928.

Probe: pre-seed manifest-covered `semantics.db` with non-SQLite bytes, then run one valid retained
intake. Result: uncaught `DatabaseError: file is not a database`, **one canonical paid object**, one
bootstrap marker, and **zero real receipt rows**. The H6 repair moved a write-critical dependency
to the common semantics store without moving its prepare/validate boundary before staging. This
recreates the paid-object/no-receipt split that the prior store-preparation contract exists to
prevent.

Required control: corrupt/unmigratable common semantics/event store + valid archive must refuse
before staging/publication, leave zero objects and zero real acquisitions/attempts, and return a
named fail-closed result. The common store must be prepared as an active write dependency without
touching the inactive acquisition counterpart.

### 2. Critical — semantic writer/load validation is not total; malformed governed state can open the horizon gate or crash

The write path validates version and retrieval instant but coerces `active` by truthiness at line
2021. The load query omits attachment `retrieved_at` (lines 2158–2162), converts any stored active
value with `bool()` (line 2222), parses adjudication parents outside a fail-closed guard (line
2211), and assumes the evidence BLOB/size types are valid before `len()`/hashing (lines
2182–2195).

Independent probes:

- writer input `active="false"` was accepted as `written` and reduced to a **known, Phase-C-eligible
  redraft assertion**;
- after a valid assertion, restoring `semantic_attachments.retrieved_at='not-a-date'` still reduced
  to known/eligible instead of unknown;
- restoring malformed adjudication JSON raised bare `JSONDecodeError`;
- restoring an integer `evidence_blob` raised bare `TypeError`.

This contradicts the accepted C2/H3 rule that restored/unsupported persisted values fail closed on
every read and that the writer schema is closed. Because `_horizon_is_effective()` controls
analysis readiness, the first two cases are fail-open, not cosmetic schema looseness.

Required controls: one mutation per persisted semantic field/type, including active, attachment
retrieval instant, parents JSON, BLOB, byte count, ids, key, retention, and allowlisted vocabulary.
Every unsupported restored state must return deterministic `unknown` without raising; every writer
shape violation must refuse before mutation. No boolean coercion may define an active assertion.

### 3. High — an unreadable attempts relation is erased as “no attempts,” bypassing literal row 9

`_store_rows()` marks acquisition-query errors unreadable (lines 1350–1369), but `_load_attempts()`
silently `continue`s on any SQLite error (lines 1943–1958). Probe: create a valid retained
acquisition, represent a restored/incomplete governed ledger by removing its `attempts` relation,
then reopen. The read model rendered ordinary `current` copy with a healthy clock instead of
`unverifiable / Footballguys refresh record unreadable`.

Required control: missing, malformed, wrong-column, and non-SQLite attempt relations in either
acquisition store must all feed the same row-9 unreadable state as the acquisition relation; a
healthy sibling store must not mask them. An explicitly versioned legacy-no-attempts shape, if it
is to remain readable, needs a named state and contract rather than the generic SQLite-exception
eraser.

### 4. High — `event_sequence` is an allocator, not a governed global event ledger

The common table stores only an autoincrement integer (lines 1332–1335). Acquisition and attempt
rows copy that integer into separate databases (lines 1891–1915 and 1934–1940), while reads trust
the copied values directly (lines 1943–1975, 2366–2395). No event identity/type/store/row binding,
foreign relationship, or load-side reconciliation exists.

Probe: normal equal-instant receipt then cross-store failed attempt produced central sequence rows
`[1,2]` and the required failed-attempt suffix. Replacing the observation attempt's claimed
sequence `2` with `1` while leaving the central ledger `[1,2]` unchanged removed the suffix and
rendered healthy `current`; no integrity/unverifiable state appeared. This is the skewed-restore
class already in scope for the independently backed SQLite stores.

Required control: every acquisition/attempt event claim must be bound to, and revalidated against,
one central event record carrying enough identity to prove the event. Duplicate, missing,
unmapped, wrong-store/type, or skew-restored claims must fail closed; query/restore order cannot
choose copy. A bare allocated number is insufficient evidence of global ordering.

### 5. High — the inactive-store byte-freeze RED never reaches the lookup, and the real success path creates a WAL file

The v5 H7 test fingerprints the inactive database, then supplies `b"not-a-zip"` at test lines
2474–2476. Archive validation fails before `_same_offering_row()`, so the test passes without
executing the lookup it names.

Probe: create the exact legacy inactive observations store, fingerprint it, then run a **valid**
retained intake. `_classify_main()` alone changed the inactive file set from one 16,384-byte main
database to that same main plus a new zero-byte `observations.db-wal`; the valid intake completed
`review_required`. Main bytes remained identical, but the accepted contract permits only SHM
appearance/mutation and explicitly freezes main/WAL membership and bytes.

Required control: both active modes must use a valid archive and an existing inactive legacy/current
store so the real lookup executes. Fingerprint main/WAL membership, size, and SHA before/during/
after; only the framed SHM residue may differ. Include the main-only WAL-mode shape, because the
existing main+WAL fixture cannot catch creation of an absent WAL.

## Reproduced gates and adequacy checks

- Strict RED v5: `PYTHONDONTWRITEBYTECODE=1`, Python 3.14, `-W error`, `--tb=no` — **249 passed,
  exit 0**.
- `py_compile` under `-W error`: exit 0.
- Ruff on `src`, `app`, and RED v5: clean.
- Full suite with only the standing untracked cadence RED excluded: **5,482 passed / 12 skipped /
  9 xfailed, exit 0**.
- A tracked-files-only auxiliary run: 4,203 passed / 1 skipped / 9 xfailed; this narrower census is
  not used as the binding full-suite result.
- Post-commit divergence audit: exact declared path/count scope; both submitted pins byte-exact;
  no execution-surface divergence after `21cd11d`.
- Passing H7 sub-boundary: the active-store preparation itself does not migrate the inactive
  acquisition schema. The failure is specifically the real lookup's physical side effect.

## Disposition

`21cd11d` is **NOT CLEAR** and remains unpushed provenance. No first capture may run against it.
RED v5 is inadequate for the five sibling cases above: each currently passes while the committed
behavior is broken. A Codex-authored RED v6 should bind these cases before the GREEN is repaired;
the pair then travels together in one reviewed act on David's word. No scheduler, provider contact,
push, or Phase B/C/D opens from this review.

H2 QB rushing remains **UNDER TEST** with no result and is unrelated.
