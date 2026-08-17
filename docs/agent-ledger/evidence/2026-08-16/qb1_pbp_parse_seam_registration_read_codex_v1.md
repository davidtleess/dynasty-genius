# QB-1 PBP parse-seam registration read — Codex v1

Date: 2026-08-16  
Disposition: **IMPLEMENTATION, not amendment; separate bounded word required**

## Registered basis

The registration pins `pbp posteam → offense_team at parse` in §5 and makes an
absent normalized manifest column a named `manifest_column_missing` refusal. Section
11 describes the admitted study input as a parsed, non-empty frame. The study source
gate likewise says ingestion lives in the shared `nflreadpy_qb_adapter.py` adapter and
that it consumes that adapter's `(frame, metadata)` outputs.

The admitted snapshot path presently verifies and reads the raw Parquet files, then
hands those raw frames directly to `load_validation_sources`. The adapter's registered
PBP parse performs the REG filter and the already-pinned
`VALIDATION_PARSED_RENAMES["pbp"]` mapping, while the matrix correctly expects the
post-parse name `offense_team`. The observed `pbp: offense_team` refusal is therefore a
missing application of an already-registered transformation, not a request to change a
registered value.

## Exact implementation boundary

- Preserve hash-before-parse receipt admission and the pinned raw files byte-for-byte.
- After receipt admission, before the parsed-frame source gate/matrix, apply the shared
  adapter's existing registered parse semantics; do not create a second parser or a
  competing rename table.
- For PBP this means its registered REG filter and exact
  `posteam → offense_team` rename on a defensive frame copy.
- Preserve every metadata/provenance field and every named fail-closed guard.
- Add contracts proving raw `posteam` is normalized once, normalized input cannot fork
  semantics, non-REG rows do not enter the parsed study frame, and missing source
  columns still refuse by the registered name.
- No input mutation, provider fetch, registered-value/pin/gate change, publication,
  commit, or push.

This seam is outside Round 14's authorized two-file predicate scope. Implementing it
requires David's separate bounded-round word. The already-authorized Round-14 rerun is
not authority to repair it; that rerun may only demonstrate the current named
fail-closed terminal state.

H2 QB rushing remains **UNDER TEST**. A failed execution is not a registered result.
