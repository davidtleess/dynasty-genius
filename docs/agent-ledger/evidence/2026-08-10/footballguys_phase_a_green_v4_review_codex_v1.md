# Footballguys Phase A GREEN v4 adversarial review — Codex v1

**Date:** 2026-08-10  
**Reviewed commit:** `8a99bd98653d513b72ab0457a6b08bac0da0e228`  
**Parent:** `d47aed19c331c09390d87b7a26c2b4fa28a54b96`  
**RED v4:** `tests/contract/test_footballguys_phase_a_red.py` —
`45d7e6f4cd865d55ed024c1829dbd0c0f9f1b6ab77cfa3b1554a94493ce7966e`  
**GREEN:** `src/dynasty_genius/sources/footballguys_intake.py` —
`aaecb2d8c5f80b8f9713199c2adf625d4011af072c988b9e109bf8a3dd216ec7`  
**Layer:** 1, intake/persistence  
**Verdict:** **NOT CLEAR — 2 Critical, 5 High. Keep the commit unpushed and do not run a first capture.**

## Outcome first

The landing itself has no scope divergence: it is exactly three modified files and `+744/-67`;
the two submitted pins reproduce from the commit; the working copies are byte-identical to those
committed blobs; and `git diff --check` is clean. The disclosed stale-bytecode defect is also
closed in source: cache-independent `compile(..., -W error)` passed and an AST walk found zero
`return` nodes under any `finally` block.

Contract conformance is green but falsification is not. RED v4 passes **222/222 with process exit
0**, and Ruff is clean. Seven untested sibling cases below still break the frozen framing, including
one path that publishes a paid archive object and then crashes before its receipt exists.

## Findings

### 1. Critical — adjudications are not bound to the target key/active parents; a public write can make the next intake orphan a paid object

`write_semantic_adjudication()` checks only that the selected assertion id exists somewhere in the
database (`footballguys_intake.py:2017-2026`). It does not require that the selected assertion:

- belongs to the adjudication's `key`;
- is one of that key's active parent assertions; or
- is included in the adjudication's parent set.

The reducer then treats any truthy authority/provenance as governed and assumes `next(...)` will
find the selected id among the target key's active assertions (`:384-390`, `:419-424`).

Independent public-API probe:

1. write active `old=redraft` and `new=dynasty_startup` assertions for the horizon key;
2. write active assertion `other` for a different key;
3. call `write_semantic_adjudication(key=horizon, parents=[old,new], effective=other)`;
4. the writer returned `{"status":"written"}`;
5. `semantic_state(horizon)` raised bare `StopIteration`;
6. a valid unit-bundle intake then published one canonical `.zip`, raised `StopIteration`, and
   left **one object / zero receipt rows**.

That is the exact payload-before-receipt split the lifecycle was built to prevent. The writer must
fail before publication unless the effective assertion is an active parent for the same key; the
load reducer must independently validate the same relation and return fail-closed `unknown`, never
raise.

### 2. Critical — semantic governance is writer-only; restored/corrupt persisted state can falsely open the horizon gate

The load path reads attachment retention/hash/size but drops attachment provenance and retrieval
provenance (`:2056-2064`, `:2094-2100`). It reads assertion claims and adjudication authority/
provenance but never re-applies the writer allowlists (`:2102-2124`). `_adjudication_is_governed()`
only checks that those values are nonempty, not allowed (`:384-390`).

Independent persisted-state probes, each starting from a valid public write:

- change attachment provenance to `untrusted-blog` → state remained `known/redraft`,
  `eligible_for_phase_c=True`;
- change the persisted claim to `weekly_projection` → state became
  `known/weekly_projection`, `eligible_for_phase_c=True`;
- insert an adjudication with authority `attacker` and provenance `untrusted-blog` over a valid
  two-claim conflict → state became `known/dynasty_startup`, `eligible_for_phase_c=True`.

These are data-corruption/restore cases, not an attacker guarantee. The acquisition reducer already
revalidates persisted identity because restores do not sign the write contract; semantic evidence
needs the same fail-closed load boundary. As written, `_horizon_is_effective()` (`:1815-1817`)
accepts any `known + eligible` value, so an unsupported persisted claim can also promote a receipt
to analysis-ready.

### 3. High — semantic assertion/evidence identity and retrieval schema are incomplete

Three public writer cases pass that should refuse:

- same assertion id + unchanged assertion tuple + same evidence id + **different evidence bytes**
  returns `noop`, because the assertion-id early return occurs before evidence identity validation
  (`:1935-1953`);
- a new assertion reusing an evidence id with the same bytes but `retrieved_at=not-a-date` returns
  `written`; only the hash is compared (`:1957-1965`), so the incoming metadata is silently ignored;
- a first assertion with `retrieved_at=not-a-date` returns `written` and immediately produces a
  `known`, Phase-C-eligible horizon (`:1974-1985` stores the string without validation).

A wrong-type version is also accepted: after versions `1` and `"two"` are written, the next
semantic read raises `TypeError` from `max(..., key=version)` (`:408-416`). The seam needs a closed
record schema, canonical validated evidence retrieval instant, typed/ordered version, and full
attachment equality before either assertion or evidence idempotency can return `noop`.

### 4. High — an unreadable acquisition ledger is silently rendered as no record

`_store_rows()` converts any SQLite query error into `[]` (`:1306-1323`), and `_load_attempts()`
silently skips an unreadable store (`:1890-1905`). A receipts file containing non-SQLite bytes
therefore produced this public read model:

```json
{"status":"no_record","copy":"No Footballguys refresh recorded","clock_id":null,"pill_delta":1}
```

Framing row 9 requires `unverifiable / Footballguys refresh record unreadable`. The existing RED
injects `{"status":"ledger_unreadable"}` directly into the pure evaluator, so it passes even though
the production loader never emits that state. Store classification/errors must enter the reducer
as the row-9 state, not disappear as an empty collection.

### 5. High — the evaluator does not select the newest attempt; it can describe two mutually exclusive newest attempts

`evaluate_refresh_state()` computes `any(failed)` and `any(invalid)` over the whole attempt history
and appends both suffixes independently (`:533-545`). Given one newer failed attempt and one newer
invalid attempt, it emitted:

> `... · newest attempted drop failed intake · newest attempted drop's refresh time unverifiable`

The framing freezes one **newest** attempt and stage 2 appends exactly one suffix. The reducer must
select one latest valid attempt-order key first, then project its single status. RED v4 exercises
failed and invalid overlays separately, so both-at-once passes broken code.

### 6. High — the claimed shared event sequence is per database, so equal-instant cross-mode ordering is false

Each acquisitions database creates its own `event_sequence` table (`:1249-1252`), and both success
and failure allocate from whichever store is active (`:1840-1845`, `:1877-1887`). The read side
then compares `(instant, event_seq)` as if the sequence were global (`:2261-2290`).

Independent transition probe at one fixed process instant:

1. option-1 receipt succeeds in `receipts.db` with `event_seq=1`;
2. mode changes to metadata-only and a later malformed intake is recorded in `observations.db`
   with `event_seq=1`;
3. the read model treats the later failure as not newer and omits the required failed-attempt
   suffix.

The event order must be globally comparable across both stores (or derive from one governed event
ledger); per-store counters cannot break equal-instant ties. RED v4 tests equal-instants only within
one database.

### 7. High — the supposedly logical-read-only counterpart path performs schema and application writes

`_prepare_stores()` initializes the active store and then calls the same write-capable
`initialize_database()` on any existing inactive counterpart (`:1763-1770`). That path alters
legacy tables, sets `user_version`, creates tables, and writes the bootstrap marker
(`:1205-1253`, `:1293-1300`).

Independent probe: with metadata-only active and an exact legacy `receipts.db` present, a malformed
observation intake changed the inactive receipt main-file bytes and added `source`, `role_records`,
`event_at`, and `event_seq`. The framing's counterpart contract says no schema or application row
may change; only SHM materialization is permitted. Migration of the active write store may remain,
but counterpart lookup/validation must be genuinely logical-read-only or be separately framed as a
mode-transition migration.

## Falsification matrix

| Input class | Probe / evidence | Result |
|---|---|---|
| valid nominal | strict RED v4, six known-answer anchors, valid archive/semantic/adjudication flows | 222/222 pass |
| boundary | equal-instant cross-store transition; failed+invalid history | findings 5-6 |
| missing | missing semantic evidence remains review-required; empty stores produce no-record | pass |
| null / API misuse | missing required mapping fields fail loud; no silent default used as evidence | in-scope boundary holds |
| wrong type | semantic version `"two"` accepted beside integer `1` | finding 3; later read `TypeError` |
| malformed shape | non-SQLite acquisition store; cross-key adjudication; malformed evidence time | findings 1, 3-4 |
| duplicate / conflict | same assertion/evidence identities with changed bytes; two attempt statuses | findings 3, 5 |
| empty collection | evaluator/store no-record positives | pass |
| cross-component shape | receipt/observation sequence; inactive counterpart DB | findings 6-7 |
| numeric edge | archive caps and day-30 boundary remain covered by RED; semantic version type is unclosed | finding 3 |
| synthetic / override | fault hooks pass, then actual persisted SQLite/object boundaries challenged independently | hooks do not cover findings 1-7 |

## Checks run

- exact commit/parent/name-status/numstat and both committed SHA-256 pins;
- `git diff --check 8a99bd9^ 8a99bd9` — pass;
- cache-independent Python 3.14 source compile under `-W error` — pass;
- AST scan for any `return` below a `finally` body — zero;
- `.venv/bin/python3.14 -W error -m pytest -q tests/contract/test_footballguys_phase_a_red.py`
  — **222 passed, exit 0**;
- `.venv/bin/ruff check src app` — pass;
- full tracked-suite-equivalent run excluding only the standing untracked cadence RED — **pending
  at artifact draft time; final census is recorded in the ledger disposition**;
- isolated temporary-root probes described above; no real Footballguys provider bytes or runtime
  stores were read or changed.

## Required next gate

Keep `8a99bd9` unpushed and prohibit first capture. A Codex-authored RED v5 should bind each real
boundary above before GREEN repair; RED v5 and the repair should land together only after a new
reviewed act and David's word. No provider contact, scheduler, push, or Phase B/C/D work opens from
this review.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
