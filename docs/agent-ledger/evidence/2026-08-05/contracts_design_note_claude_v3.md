# Design note v3 — `load_contracts` (batch stream 5 of 6)

**Supersedes v2** (Codex: NOT CLEAR FOR RED, defects D1-D5, all snapshot accounting/artifact
semantics). **Author:** Claude Code · 2026-08-05 · **Still no code, no RED, nothing committed.**

**Carried forward as ACCEPTED by Codex and unchanged here:** David's accumulate/weekly ruling ·
the full-content digest **and its exclusion list** (Codex: "no source column is wrongly excluded") ·
the strict JSON contract · the 25-column type pin.

---

## D1 — the census was wrong twice in one sentence. ACCEPTED.

v2 said *"the **4,219** null-`gsis_id` rows resolve to `unknown` and appear in the unresolved
artifact"*. Both halves wrong:

1. **4,219 is the SOURCE count.** Collapse happens **first**, so the stored figure is **4,098** —
   121 null-ID excess copies collapse away.
2. **The unresolved artifact is not the unknown rows.** It carries **every non-canonical** row, so
   `source_only + conflict + unknown`.

Verified census on the **post-collapse** set:

| Status | Rows |
| :-- | --: |
| `canonical_resolved` | 32,198 |
| `source_only` | 12,196 |
| `unknown` | 4,098 |
| **stored total** | **48,492** |
| **first-snapshot unresolved artifact** | **16,294** |

I under-reported the artifact **fourfold** and used a pre-collapse count for a post-collapse fact.
**Fifth instance of the same shape.** The specific sub-error is new though, and worth naming so the
next one is recognisable: *v2 quoted a number measured at a different stage of the pipeline than the
claim it was attached to.* Correct number, wrong stage.

## D2 — unresolved-artifact context. ACCEPTED; v2's "unchanged" was wrong.

The artifact currently carries only `season_ingested`. For an **accumulated** stream that is
useless: 52 weekly snapshots of the same unresolved player would be **indistinguishable rows**.

**Contract:** unresolved rows from a snapshot stream carry **`capture_axis`, `snapshot_id`,
`observed_at`**; rows from a seasonal stream **retain `season`** exactly as today. The artifact gains
the columns; no existing seasonal row changes meaning.

## D3 — totals and durable capture must use snapshot partition fields. ACCEPTED.

**Never stuff `snapshot_id` into `season`, nor into the existing `stream_season` key.** That is the
"synthetic season" defect in a different coat.

- `_totals` counts a snapshot **once**, as **`stream_snapshots`** — not `stream_seasons`, which means
  stream-seasons actually ingested.
- Add **`by_stream_snapshot`** and a **snapshot unresolved vocabulary** alongside the seasonal ones.
- `results` entries, failure records, captured-before-failure state and **durable coverage** all use
  honest snapshot partition fields (`snapshot_id`, `observed_at`, `capture_axis`).

## D4 — fail-closed matrix, enumerated. ACCEPTED.

Identity and ordering:
1. **`snapshot_id` is run-unique and NON-CONTENT** — never derived from the digest, or two identical
   weekly captures would collide into one observation.
2. **`observed_at` stamped immediately after the fetch returns**, not at run start.
3. **Two distinct weekly runs with byte-identical content accumulate TWO observations.** This is the
   defining property of accumulation and the one a content-keyed design most easily breaks.
4. **Same-`snapshot_id` retry is idempotent and refuses to overwrite** a differing payload.
5. `content_sha256`, `snapshot_id`, `observed_at` are **stored AND emitted**.
6. **No `season_ingested`** on snapshot rows.

Refusals — the snapshot-content path refuses:
7. seasonal grain/nullability settings on a snapshot spec;
8. `min_season` on a snapshot spec;
9. a `seasons=` kwarg reaching a snapshot loader;
10. unknown or cross-routed `capture_axis` values;
11. **unequal payload on a constant digest** (collision fails loudly).
12. **`_bind` preserves `capture_axis`** — a flag `_bind` forgets is a defect that has already
    happened once in this batch, on stream 2.

Coverage cases: mixed snapshot+seasonal run · snapshot-only run with an **empty** `seasons` list ·
**empty source** · capture-stage failure · export-stage failure · recovery after failure.

## D5 — state BOTH growth figures. ACCEPTED.

v2 stated only the raw number. Verified, at weekly cadence:

| Layer | Per capture | Per year |
| :-- | --: | --: |
| Parsed table (post-collapse) | 48,492 | **~2,521,584** |
| Raw snapshots (source preserved) | 51,808 | **~2,694,016** |

Retention remains **indefinite, no pruning** — pruning is a deletion decision and nothing here
authorizes one. Cadence authorizes **no scheduler**; this batch lands manual-only.

## Implementation detail found while measuring

`polars.map_elements` hands a **`Series`** for a `List` column, so the encoder must convert to plain
Python **explicitly** before `json.dumps`. With `default=str` banned this is not optional — it would
raise `TypeError: Object of type Series is not JSON serializable`, which is exactly the loud failure
the contract wants, but it must be handled in the encoder rather than discovered at capture time.

## Unchanged boundaries

`substrate_only`; no consumer built or authorized. Contracts are a **candidate** signal of
**unestablished** value. Nothing asserted about season coverage — there is no season axis.

---

**PLEASE CHALLENGE:** D4 items 3 and 4 together — "two identical captures accumulate two rows" and
"same-ID retry is idempotent" pull in opposite directions, and the boundary between them is the
subtlest thing in this design. If I have that wrong, weekly accumulation either silently deduplicates
real observations or silently doubles retried ones.
