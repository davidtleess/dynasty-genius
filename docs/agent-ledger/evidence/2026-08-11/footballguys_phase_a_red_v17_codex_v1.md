# Footballguys Phase A RED v17 — Codex authorship record

**Date:** 2026-08-11  
**Layer:** Layer 1 — ingest/persistence  
**Authority:** implementing lane accepted all three findings from the adversarial review of
commit `1e5492b9bb540a45be4fe451000d9d72af0a3130` and explicitly requested Codex-authored RED v17.  
**Framing:** Phase A framing v25 remains the source of record. This RED opens no GREEN, runtime
write, first capture, provider contact, scheduler, push, or Phase B/C/D work.

## 1. Pins and scope

- **RED v17:** `tests/contract/test_footballguys_phase_a_red.py`
- **RED SHA-256:** `00299c99798dbfd1c6bb582704b7b143fd3e70ae8bf6e45babf5d0d182ce4689`
- **Size:** 5,500 lines / 213,411 bytes
- **Baseline GREEN:** `src/dynasty_genius/sources/footballguys_intake.py`
- **Baseline GREEN SHA-256:**
  `63c31c1870b674ec0212fc301a2f995d909051b54c8ecac5430adf457ea4e1bb`
- **Production delta:** none. The only executable change is the RED contract file
  (`+449/-1`; the one deletion changes the module title from v16 to v17).

## 2. Binding controls

### H1 — all four semantic-table grammars are closed and operational

`test_v17_h1_every_semantic_table_has_closed_operational_grammar` supplies a canonical and a
load-bearing `CHECK` form for each non-event semantic table:

1. `semantic_assertions`: `CHECK(version > 100)` rejects the governed version-1 writer row.
2. `semantic_attachments`: `CHECK(evidence_bytes < 0)` rejects the governed attachment.
3. `semantic_evidence_objects`: `CHECK(length(evidence_blob) < 0)` makes SQLite omit the
   `INSERT OR IGNORE`; the oracle explicitly forbids returning `status="written"` when no bytes
   were stored.
4. `semantic_adjudications`: `CHECK(authority = 'nobody')` rejects the governed David ruling.

Each mutant must refuse as `store_schema_unmigratable:semantics` before its writer branch, and
the main/WAL fingerprint plus every application table remains unchanged. Each canonical sibling
executes the corresponding real writer successfully, so refusal by table name or blanket refusal
cannot pass.

### H2 — physical index signatures, not column shadows

`test_v17_h2_index_signatures_bind_physical_index_metadata` independently materializes and
inspects real SQLite indexes with `PRAGMA index_list` and `PRAGMA index_xinfo`, then exercises the
production signature predicate. The controls bind:

- uniqueness and `origin` (`pk` versus `u`);
- partial status;
- expression/key membership;
- indexed-column identity and exact sequence;
- direction (`ASC` only);
- collation (`BINARY` only);
- the distinct expected origin maps for assertion identity, event identity, and the two marker
  identities.

The five newly failing discriminators are assertion PK replaced by UNIQUE, assertion PK with
`COLLATE NOCASE`, descending assertion PK, event UNIQUE replaced by PK, and swapped marker PK/
UNIQUE origins. Canonical, partial, expression, wrong-column, and composite-sequence anchors
remain passing.

### M3 — marker grammar consumes the whole DDL

`test_v17_m3_marker_grammar_consumes_the_complete_table_ddl` covers both admitted marker bodies:

- canonical and exact legacy bodies with comment-only suffixes remain accepted;
- canonical and legacy bodies followed by `STRICT` refuse;
- canonical and legacy bodies followed by `WITHOUT ROWID` refuse.

Every negative freezes rows and the main/WAL bytes. `WITHOUT ROWID` fixtures are snapshotted by
their declared primary key rather than the absent `rowid`, so the test reaches the intended
grammar predicate.

## 3. Strict failing census

Command:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python3.14 -W error -m pytest -q --tb=no \
  tests/contract/test_footballguys_phase_a_red.py
```

Result, reproduced after the final edit:

- **472 collected**
- **13 failed**
- **459 passed**
- **process exit 1**

Failure identity is exact:

- **H1: 4** — one constrained grammar per non-event semantic table;
- **H2: 5** — PK-to-UNIQUE, NOCASE, DESC, event-origin, and marker-origin mutations;
- **M3: 4** — canonical/legacy × `STRICT`/`WITHOUT ROWID`.

The 26 new v17 cases divide into **13 failing mutants + 13 passing anchors**. No inherited test
regressed, and no skip/xfail/skipif exists in the file.

## 4. Hygiene and adequacy

- `.venv/bin/ruff check tests/contract/test_footballguys_phase_a_red.py` → clean.
- Python 3.14 strict compilation → clean.
- `git diff --check` on the RED → clean.
- The baseline GREEN hash remained byte-exact at `63c31c18…`.
- No config, manifest, runtime namespace, provider payload, scheduler, or downstream phase was
  touched.

## 5. Disposition

RED v17 is authored and intentionally failing. The implementing lane may reproduce this exact
census and author GREEN as a separate act. RED and GREEN travel together only on David's landing
word. Commit `1e5492b` remains unpushed; first capture and Phase B/C/D remain closed.

H2 QB rushing remains **UNDER TEST** with no result and is unrelated.
