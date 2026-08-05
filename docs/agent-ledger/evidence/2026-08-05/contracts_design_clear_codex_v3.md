# Contracts stream design v3 — Codex CLEAR

Date: 2026-08-05

Reviewed artifact: `contracts_design_note_claude_v3.md`

Disposition: **DESIGN CLEAR — RED may open.** No implementation or commit CLEAR is implied.

## Accepted design

- Accumulate from capture one at David's weekly manual cadence; indefinite retention, no pruning or
  scheduler authority.
- Full canonical-source `content_sha256`; correct exclusion of observation and derived fields;
  observation row key `(snapshot_id, content_sha256)`.
- Exact post-collapse census: 32,198 canonical + 12,196 source-only + 4,098 unknown = 48,492;
  first-snapshot unresolved artifact 16,294; 3,316 excess copies reconcile to 51,808 source rows.
- Honest snapshot partition vocabulary in durable coverage, status, totals, failures, export, and
  unresolved identity; never a synthetic season.
- Strict JSON, explicit Polars-Series-to-plain-Python conversion, preserved list order/types, exact
  13-field nested schema, no fallback stringification.
- Complete 25-column emitted types and separate parsed/raw growth statements.
- D4 fail-closed/refusal and empty/failure/recovery matrix.

## Binding interpretation of D4 items 3 and 4

They do not conflict. Identity has two levels:

1. A **new run-unique snapshot ID** denotes a new observation. Two weekly runs with identical
   source content and different snapshot IDs accumulate two complete observations.
2. Reusing the **same snapshot ID** denotes a retry of the same logical observation, never a later
   weekly observation. It is idempotent only when all immutable snapshot facts match: snapshot ID,
   original `observed_at`, normalized row-set/projection/coverage digest, and raw provenance/hash as
   declared by the RED. Return unchanged/no-op; do not rewrite timestamps or rows.
3. Same snapshot ID with a different observation time, payload, projection, coverage, or required
   provenance **refuses** and preserves the first successful snapshot. A retry cannot update an
   observation into a different observation.

The digest used for this snapshot-level idempotence must cover the same reconciliation facts the
existing seasonal apply path protects—stored rows, projection contract, and coverage counters—so a
changed duplicate count cannot hide behind identical collapsed rows. `content_sha256` remains the
per-row source-content digest; do not conflate the two digests.

## Encoder boundary for RED

The discovered Polars behavior is accepted as a required positive control: when `map_elements`
hands the encoder a `Series`, convert explicitly with an order-preserving operation such as
`to_list()`, then validate that the result is a list of mappings with exactly the 13 declared fields
and JSON-compatible values. Only then call strict `json.dumps`. Any other runtime type or nested
shape refuses by name; no generic coercion fallback is allowed.

The corrective RED should now pin these outcomes before GREEN.
