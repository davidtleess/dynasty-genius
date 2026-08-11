# Footballguys Phase A GREEN review — commit `e8fc4ec` — Codex v1

Date: 2026-08-10  
Reviewer: Codex, independent review lane  
Layer: 1 — intake/persistence  
Verdict: **NOT CLEAR — 3 Critical findings**

## Reviewed pin and divergence audit

- Commit: `e8fc4ecb48bf6f51988ab6f4d8e52e3f580336a7`
- Parent: `acaaf6b3ff491fd5269f88764c052c332a91811f`
- Declared/observed diff: exactly three modified files, `+757/-86`:
  `docs/agent-ledger/2026-08-10.md`,
  `src/dynasty_genius/sources/footballguys_intake.py`, and
  `tests/contract/test_footballguys_phase_a_red.py`.
- RED SHA-256 reproduced:
  `a5847de038524155c13cc89351414b413846f62703c209a502e34f208b01b59c`.
- GREEN SHA-256 reproduced:
  `43fddc5ef59b2c9f1352f99b7fdd6381b34d86f507204c0ba9fd0688541fbf71`.
- A later docs-only HEAD left both reviewed files byte-identical to the commit.

## Declared gates independently reproduced

- Strict RED v6, Python 3.14, `PYTHONDONTWRITEBYTECODE=1 -W error`:
  **278 passed, exit 0**.
- Full tracked suite, excluding only the disclosed untracked cadence RED:
  **5,511 passed / 12 skipped / 9 xfailed, exit 0**.
- `uvx ruff check src app`: clean.
- Cold `py_compile -W error`: clean.
- Reviewed RED/GREEN diff from the committed pin to the current tree: empty.

Those gates are real. They do not cover the three cases below.

## Findings

### C1 — Critical — restored semantic evidence still fails open into Phase-C eligibility

The load-side validator is not the promised total mirror of the writer. At
`footballguys_intake.py:2344-2364`, attachment retrieval time is parsed with
`_canonical_instant(..., now=None)`, so the write-side future-time constraint is removed during
load. At `2366-2373` the attachment identity key is accepted without the writer's nonempty-string
predicate. The writer itself indexes required fields directly at `2124-2166`, so a missing field
raises a bare `KeyError` instead of the named domain refusal promised by the total schema.

Live probes against the committed pin:

1. Write a valid provider-authentic horizon assertion, then restore
   `semantic_attachments.retrieved_at='2099-01-01T00:00:00Z'`.
   `semantic_state()` returned `state='known'`, `value='redraft'`, and
   `eligible_for_phase_c=True`.
2. Restore both the assertion and attachment `evidence_id` fields as the same BLOB
   `b'bad-id'`. The state again returned known/eligible and exposed the BLOB as its evidence id.
3. Delete `attachment.evidence_bytes` from an otherwise valid writer record.
   `write_semantic_assertion()` raised bare `KeyError('evidence_bytes')`.

This is load-side semantic promotion from evidence the governed writer would refuse. Required RED
siblings: future restored evidence time; non-string/empty restored evidence identity; missing and
wrong-type fields across both writer sections, asserting named refusal/state and never a bare
exception.

### C2 — Critical — event reconciliation is one-directional and missing claims are trusted

`_event_claims_valid()` only appends rows whose copied `event_id` is truthy
(`footballguys_intake.py:2602-2622`) and returns `True` when that leaves no claims
(`2622-2623`). It then checks only `claim -> central` membership (`2624-2638`); it never checks
that central acquisition/attempt events have a matching store row. This contradicts the accepted
missing/unmapped/skewed fail-closed boundary and also makes the v1-v4 migration unsafe: migration
adds nullable event columns to legacy rows and nullable identity columns to the former bare central
sequence, after which the reader treats the absence of proof as success.

Live probes:

1. After a valid retained intake, set only the acquisition's `event_id=NULL`. The reducer rendered
   ordinary `current` with that receipt as the clock instead of the event-ledger integrity state.
2. With effective horizon evidence seeded first, the same mutation preserved the receipt as
   `latest_analysis_ready_id`.
3. Delete the acquisition row while retaining its central `acquisition` event. The reducer rendered
   `no_record`; the unpaired central event was silently ignored.

The writer makes this state reachable without out-of-model mutation: `_allocate_event()` commits
the central record before the separate acquisition/attempt transaction, so a crash or second-store
failure between those commits leaves exactly such an orphan. Required RED siblings: null/empty
copied event identity; central event without its acquisition/attempt; legacy migration with
unbound rows; and both cross-store restore directions. Every case must render the named integrity
state, never a healthy clock/no-record fallback.

### C3 — Critical — `immutable=1` preserves WAL bytes by ignoring their committed state

All acquisition and attempt loads use SQLite `immutable=1`
(`footballguys_intake.py:1428-1438`, `2085-2091`), and counterpart classification does the same
at `1530-1539`. The comments assert that every connection is checkpointed, but an inactive store
can legitimately be restored or recovered as `main + WAL` without SHM—the exact physical shape
the earlier byte-level contract admitted. SQLite immutable reads do not replay that WAL.

Physical and product-level probes:

1. A WAL database with a committed table and row present only in WAL reported no table through
   `mode=ro&immutable=1`; `SELECT` failed with `no such table`.
2. Starting from a valid current receipt store, commit `DROP TABLE attempts` into WAL with
   autocheckpoint disabled, copy the coherent `main + WAL` snapshot to a fresh governed root, and
   remove only SHM. The production immutable reader still saw the old empty attempts table and
   rendered healthy `current` rather than framing row 9.
3. Opening that same snapshot with ordinary `mode=ro` replayed the WAL and correctly returned
   `no such table: attempts`; main and WAL remained byte-stable and only SHM appeared, which is the
   already-framed permitted residue.

RED v6's H5 fixtures at `test_footballguys_phase_a_red.py:2865-2892` create legacy/current stores
whose writers have closed and checkpointed; they assert byte freeze but never place committed
state in WAL. This is another test of the promise's shadow. Required RED: both retention modes
over a valid archive and an inactive `main + nonempty WAL + no SHM` store, asserting (a) committed
WAL state is observed, (b) the corresponding row-9/conflict state renders, and (c) main/WAL
membership, size, and SHA remain frozen while SHM alone may appear.

## Disposition

`e8fc4ec` is **NOT CLEAR** and must remain unpushed. No first capture may run against this pin.
Do not author RED v7 or repair GREEN until the implementing lane accepts or contests these exact
findings. If accepted, RED v7 should bind the three probe families above; RED and GREEN again land
together only on David's word.

No provider contact, scheduler, capture, runtime-store mutation, push, or Phase B/C/D work was
performed. H2 QB rushing remains **UNDER TEST** with no result and is unrelated.
