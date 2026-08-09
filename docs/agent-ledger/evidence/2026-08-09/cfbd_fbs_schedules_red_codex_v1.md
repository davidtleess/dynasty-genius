# CFBD FBS schedules capture — RED v1 implementation-lane packet

**Layer:** 1 ingest. **GREEN is not open pending independent review.** No CFBD data request was
made while authoring this contract, no key was printed, and no scheduler, consumer, model, feature,
commit, or push action occurred.

## Pin and RED evidence

- Contract: `tests/contract/test_cfbd_fbs_schedules_capture_red.py`
- SHA-256: `1656a73e29711beca9273e1dbfd2343149a20a93505c5cf820d1aa54a53ef3f7`
- Size: 879 lines
- Focused RED: **107 failed / 1 disclosed pass**, true pytest exit 1, zero setup or collection
  errors. The disclosed pass (`O1`) verifies the committed provider contract and cannot exercise
  the absent GREEN.
- Ruff: clean.
- Whole-suite collection: **5,173 collected**, zero collection errors.

## Source contract independently anchored before implementation

The committed provider artifact is
`docs/provider-contracts/cfbd/openapi.json`, SHA-256
`f6274010fb8f3d11c4c574fd4d648fd33e6c47e0eca2cfb61b481b20ca482ea3`, CFBD API
v5.21.0. Its `GET /games` operation accepts `year`, `seasonType`, and `classification`, and its 200
response is a top-level array of `Game` objects. The requested offering is exactly:

`https://api.collegefootballdata.com/games?year=2026&seasonType=both&classification=fbs`

The bearer key is header-only. The successful request count is exactly one. The response's
`X-CallLimit-Remaining` value is retained as `call_limit_remaining_after`; no extra usage request is
permitted for accounting.

## Contract shape

1. **Transport and provider identity:** exact URL and query, one authenticated request, JSON content
   type, exact HTTPS host/path after redirect, timezone-aware retrieval timestamp, provider Date
   header, request count and remaining-call evidence. Foreign, look-alike, HTTP, path-swapped, or
   credential-bearing delivery URLs fail closed and cannot leak credentials.
2. **Raw before parse:** exact response bytes, byte count and SHA-256 are retained under both a
   content address and a check address before canonical interpretation. Invalid retrieved bytes are
   quarantined; transport failures publish no raw payload.
3. **Lossless canonicalization:** every provider key and nested value survives. The vintage carries
   an independently recomputable ordered per-object JSON type schema and SHA-256. Inconsistent
   object order/schema is refused rather than silently unioned.
4. **FBS scope and game validity:** all 34 committed OpenAPI-required fields exist on every row;
   their JSON types are validated; ids are unique; every row is season 2026; at least one opponent
   is FBS. FBS-vs-FCS is a required positive control. Provider-naive and timezone-aware
   `startDate` values are both valid and retained verbatim; date-only or impossible values fail.
5. **No finality invention:** `completed`, scores, and nulls are retained verbatim. No derived
   `status` or `finality` field reaches canonical games.
6. **Durability:** content-address integrity is verified on reuse. Identical bytes create another
   paid check/accounting event but no duplicate vintage; `last_checked` advances and
   `last_changed` freezes. Changed bytes create a second retained vintage. Transport and all four
   injected publication-boundary failures preserve the prior marker/index, leave no temp artifacts,
   and append a failed audit.
7. **Operational surface:** the CLI refuses a missing key before transport creation and supports an
   injected one-request fetch-to-publish test. The exact default store must be a required backup
   directory. All canonical paths are containment-checked.

## Seeded falsification matrix

| Class | RED probes |
|---|---|
| valid nominal | FBS/FBS, FBS/FCS, aware/naive kickoff, null and completed scores |
| boundary | week 0, postseason-compatible schema, call-limit remaining 0 |
| missing/null/wrong type | every required identity/scope/date field and all OpenAPI scalar/array/object families |
| malformed shape | non-JSON, object root, non-object array member, non-finite JSON, empty array, inconsistent ordered object schema |
| duplicate/conflict | identical and conflicting duplicate provider game ids |
| cross-component | exact request/header, redirect identity, CLI, manifest, marker/vintage provenance |
| numeric edge | bool rejected as integer; call-limit negative/bool rejected |
| synthetic/override | injected transport, changed content, corrupted content address, 3 fault shapes x 4 storage boundaries |

## Implementation-lane questions for independent review

1. Is retaining each paid replay as a new **check/accounting event** while deduplicating only the
   content vintage the correct audit grain? The alternative (deduplicating the check) would erase
   real paid-call consumption.
2. Is exact ordered-key consistency across every response object too strict for this provider, or
   required by the requested ordered per-object schema/type hash? Raw bytes remain lossless either
   way; this choice determines whether harmless serializer reordering is accepted or quarantined.
3. Should a missing/invalid `X-CallLimit-Remaining` header block publication, as RED v1 requires,
   or publish with call accounting marked unavailable? The implementation lane chose fail-closed
   because actual paid-call accounting is an explicit ticket acceptance item.

The implementation lane's own current read is that all three are appropriately strict for a first
paid capture, but that read is not a clearance. GREEN waits for the independent lane's disposition.
