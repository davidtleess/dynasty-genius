# CFBD FBS schedules RED v2 — independent review

Date: 2026-08-09  
Layer: 1 — source capture and retained provenance  
Reviewer: Codex  
Verdict: **NOT CLEAR**

## Reviewed pin and checks

- `tests/contract/test_cfbd_fbs_schedules_capture_red.py`, 879 lines:
  `1656a73e29711beca9273e1dbfd2343149a20a93505c5cf820d1aa54a53ef3f7`
- Independently recomputed the pin.
- Focused pytest: **107 failed / 1 disclosed pass**, true exit 1, zero setup or collection errors.
  The failures are the intended absent-module RED state; O1 is the disclosed committed-contract
  control.
- `uvx ruff check`: **clean**.
- Re-read committed CFBD OpenAPI v5.21.0, SHA-256 `f6274010…`, including `/games`, `Game`,
  `GamePlayoff`, `SeasonType`, `DivisionClassification`, `PlayoffCompetition`, and `PlayoffRound`.

## Consolidated findings

### F1 — JSON member order is being treated as source schema, and additive drift is simultaneously required and forbidden

F4 refuses two Game objects with the same keys and values solely because their serialized member order differs. JSON objects are unordered by definition; order belongs to the raw byte artifact, which is already retained exactly, not to the logical schema. This would quarantine a valid provider response after an inconsequential serializer change.

At the same time, F1 requires accepting `newProviderField`, while the pinned Game schema explicitly has
`additionalProperties: false` (`openapi.json:2999-3001`). Those rules conflict: the contract claims the
OpenAPI schema is authoritative but requires GREEN to accept a response the schema declares invalid.

Repair: preserve the exact raw bytes, but derive the logical schema in a deterministic order independent
of JSON member order. Pin the accepted Game field set to the committed OpenAPI. An additive provider
field should be quarantined as `schema_drift` pending contract refresh, not silently promoted.

### F2 — the declared OpenAPI validation is top-level only and can accept corrupt nested or enum values

The contract checks that required top-level fields exist and samples broad Python container types, but it
does not pin the provider's actual schema:

- `seasonType` can be any non-empty string; a response value outside `regular`/`postseason` passes.
- the non-FBS side's classification can be any string, despite the `fbs/fcs/ii/iii` enum
  (`openapi.json:2571-2578`).
- integer fields have no float mutant, so `id=401752001.0` can pass a weak numeric validator.
- nested `NaN`/`Infinity` is untested; `[NaN]` only proves rejection of a non-object array member.
- non-null line-score arrays and their numeric elements are never positive-controlled or falsified.
- every fixture has `playoff=null`, so a validator that rejects every real postseason `GamePlayoff`
  object passes. The pinned object has eight required fields and two enums
  (`openapi.json:3562-3605`, `5840-5845`, `6104-6111`).
- the schema hash records only `array` or `object` at the top level; corrupt nested shapes can hash the
  same as valid ones.

Repair: add a valid postseason row with a complete non-null `playoff`, valid non-null line-score arrays,
and nullable-classification positive controls. Add enum, integer-vs-number, array-item, nested-object,
and nested non-finite mutants. Make the recomputable schema representation recursive or pair the
observed top-level schema hash with explicit full OpenAPI validation.

### F3 — reacquisition is mislabeled as replay, so the required zero-call replay is absent

A1/A2 call `capture()` twice. That is a second paid acquisition and correctly should create a second
check/accounting event while reusing the content vintage. It is not replay. The acceptance packet also
requires replay from retained bytes with no duplicate vintage. B21's precedent is a local
`store.replay(check_id)` that performs zero provider requests and mints no check or vintage.

Repair: keep the identical-content reacquisition cases, rename them, and add local replay by check ID.
Assert zero fetch calls and unchanged check/vintage/request counts, plus identical rows and raw hash.

### F4 — an optional telemetry header is incorrectly made a publication prerequisite

The pinned `/games` 200 response declares JSON content but no response headers
(`openapi.json:9240-9252`). An official provider example shows `X-CallLimit-Remaining` when present, but
the committed contract does not guarantee it. The ticket requires actual call consumption; the route
already knows that one request occurred. Remaining quota is useful telemetry, not proof that the request
happened.

Failing a valid paid response after the call is spent would discard the ticket's data for absent
auxiliary telemetry. Repair: always record actual local request/attempt count; retain a valid remaining
header when present, otherwise publish it as unavailable with an explicit accounting-quality field.
Reject malformed values only from the telemetry field, not the source payload. Cover retry attempts so
`request_count` is not hard-coded to one on failure.

### F5 — publication rollback can leave unindexed raw/check/vintage artifacts and still pass E2

E2 verifies the prior marker, the indexed vintage count, and temp filenames. It never compares raw
content/check objects or the vintage directory against the pre-failure state. A GREEN can leave the new
content object, check object, or unindexed vintage behind and pass. `_assert_empty` likewise permits raw
artifacts on validation failure. E3 covers a corrupt content object but not a corrupt pre-existing check
object.

Repair: snapshot or census every canonical artifact class before the injected failure and require them
unchanged afterward, excluding only the appended failed-audit record and intentional quarantine. Assert
no partial artifacts for each boundary/fault. Add the check-object integrity twin of E3. Every retrieved
validation failure should have one failure ledger entry with code, raw hash, request count, and sanitized
provenance; it must not create canonical raw/check/vintage artifacts in addition to quarantine.

### F6 — the secret-safety test says “CLI” but never exercises CLI output

S9 only asserts on `CaptureError` text and retained store text. It never imports or calls the CLI, and
D2/D3 cover only missing-key and success paths. This is the exact surface gap that leaked signed URL
credentials through B21 stderr after the store itself was clean.

Repair: inject a credential-bearing transport failure through `cli.main`, assert non-zero exit, and scan
stdout, stderr, exception-free output, and every retained text file for bearer, URL userinfo,
query/fragment, and authorization markers. Also cover `PublishError`/`OSError` normalization so the CLI
does not emit a traceback or secret-bearing exception.

### F7 — the production transport is not contracted

All successful tests use `RecordingFetcher`; D3 replaces `default_fetcher`. Nothing pins the real
transport's timeout/retry behavior, status handling, redirect provenance, header parsing, retrieved time,
or attempt count. A GREEN whose injected collaborator works while its production HTTP route cannot make a
valid capture would pass, repeating B21's cleared-but-unusable failure class.

Repair: contract `default_fetcher` with a mocked HTTP client at the socket/client boundary: exact URL and
header-only bearer; follow redirects; 200 response bytes and nonsecret headers; 400/401/403 no retry;
bounded retry only for the repository's shared transient policy; exact attempt count; and sanitized
terminal failure. Keep the live capture as the final falsification after GREEN.

## Disposition

**NOT CLEAR** on pin `1656a73e…`. The three implementation-lane questions resolve as follows:

1. A second paid acquisition is a new check/accounting event and the same content vintage, but a separate
   zero-call local replay contract is also required.
2. Exact JSON member order is too strict and is not schema. Preserve it only in exact raw bytes.
3. Missing quota-remaining telemetry must not discard a valid paid response; actual local request count
   remains mandatory and header availability must be explicit.

Return one revised pin and disposition covering F1-F7 before GREEN.

