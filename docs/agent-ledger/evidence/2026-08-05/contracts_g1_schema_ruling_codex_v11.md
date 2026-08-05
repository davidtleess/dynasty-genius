# Contracts G1 exact-schema ruling — Codex v11

Date: 2026-08-05  
Layer: 1 ingestion  
Disposition: **Choose a scoped third option**

## Ruling

Add an opt-in `StreamSpec.refuse_unexpected_columns: bool = False` (equivalent naming is fine if
equally explicit). Set it `True` for `CONTRACTS` only and preserve it through `_bind`.

On a non-era spec with the flag enabled, `normalize_rows` must compare the key set of **every**
record to the declared source columns and refuse with the row index plus named unexpected/missing
columns before projection, collapse, digesting, or persistence can discard the drift.

The existing missing-column refusal remains part of the exact contract. An empty snapshot remains
valid and records explicit zero because no source row exists from which a schema can be observed.

## Why this option

- Do not declare a synthetic one-era contract merely to borrow exact equality: that would add
  `source_era` to the stored/exported projection and widen the cleared contracts artifact.
- Do not extend exact equality globally in this stream: that changes the twelve frozen seasonal
  adapters' accepted-input behavior.
- A boolean is appropriate here because this is one independent binary rule — refuse or permit
  unexpected columns — unlike `capture_axis`, whose alternatives have distinct partition semantics.

## Required positive controls

1. `CONTRACTS.refuse_unexpected_columns is True`; all previously landed specs remain at the
   default and keep their normalized rows, `_rows_hash`, stored columns, and projection fingerprints.
2. An unexpected field on record zero refuses by name.
3. An unexpected field confined to a later record refuses by index and name.
4. A missing field on record zero and on a later record refuses by index and name.
5. `_bind` preserves the flag.
6. Contracts stored/emitted columns remain exactly the cleared 25 source columns plus
   `dg_player_id`, `identity_status`, `row_key`, `content_sha256`, `snapshot_id`, and `observed_at`;
   no `source_era` is introduced.

This is the authorized G1 mechanism expansion. It does not authorize global schema-policy changes.

## Other dispositions

G2-G6 are accepted as stated. Precision for G5: keep seasonal counters untouched; add explicitly
snapshot-prefixed identity totals, include the same census in `by_stream_snapshot`, and add a
snapshot-partition unresolved inventory so a snapshot-only run cannot truthfully report the
seasonal zeros as its only identity totals.
