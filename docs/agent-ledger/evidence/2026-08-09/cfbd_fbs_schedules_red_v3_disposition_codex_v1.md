# CFBD FBS schedules RED v3 — consolidated disposition

Date: 2026-08-09  
Layer: 1 — source capture and retained provenance  
Implementation lane: Codex  
Review answered: `cfbd_fbs_schedules_red_review_codex_v1.md`

## Revised pin and RED gates

- `tests/contract/test_cfbd_fbs_schedules_capture_red.py`, 1,405 lines:
  `ca8ab632afe34dcd34d01913df17837892eeb10ac69839452b98f3f3b19c6396`
- Focused pytest: **168 failed / 1 disclosed pass**, true exit 1, zero setup or collection
  errors. The 168 failures are the intended absent-module/CLI RED state; O1 is the disclosed
  committed-OpenAPI control.
- `uvx ruff check tests/contract/test_cfbd_fbs_schedules_capture_red.py`: **clean**.
- Python compile: **clean**.
- Full-suite collection: **5,235 tests**, exit 0, zero collection errors.
- No provider request was made. GREEN remains closed pending independent review.

## Consolidated findings disposition

### F1 — accepted in full

The logical schema is now a deterministic field-name-sorted sequence, independent of JSON member
order; F4 positively proves a reordered object is accepted and retains its exact logical values.
Exact serializer order remains only in the retained raw bytes. The accepted field set is the pinned
OpenAPI `Game` membership. F1b now refuses an additive field as `schema_drift`, consistent with
`additionalProperties: false`.

### F2 — accepted in full

The fixture now includes valid non-null line scores and a complete postseason `GamePlayoff` object.
The contract checks integer fields against floats and booleans, every OpenAPI enum domain, nullable
classification, finite line-score members, nested non-finite JSON, all eight playoff members,
playoff enums, nested member types, missing fields, and additive nested drift. Positive controls
exercise every declared `SeasonType`, every `DivisionClassification` value plus null, and every
`PlayoffRound`. The observed top-level type hash remains recomputable and is paired with strict full
validation against the pinned OpenAPI SHA rather than pretending that one shallow hash describes a
nested document.

### F3 — accepted in full

The two `capture()`-twice cases are renamed paid reacquisition: they require two checks and two
accounted requests while reusing one content vintage. A separate `store.replay(check_id)` contract
arms the HTTP boundary to fail and requires identical retained rows/hash with byte-identical
canonical census, ledger, marker, one check, one vintage, and one total provider request.

### F4 — accepted in full

`X-CallLimit-Remaining` is nullable telemetry. Missing or malformed values do not discard a valid
response; the marker records explicit `request_count_only_header_absent` or
`request_count_only_header_invalid` quality. A valid header is retained with
`request_count_and_remaining_header`. Local request count is mandatory on success and failure, and
a three-attempt exhausted transport proves it is not hard-coded to one. No second usage request is
allowed.

### F5 — accepted in full

`_assert_empty` now covers raw content, raw check, vintage, index, and marker objects. Publication
failure snapshots hashes across every canonical artifact class and requires an identical census
after each of four boundaries under route, OS, and genuine mid-write faults; only the failed ledger
event may append. `partial_artifacts()` must be empty. The content-integrity guard now has a corrupt
pre-existing check-object twin. A 15-case audit matrix requires every retrieved validation refusal
to quarantine the exact bytes, publish no canonical artifact, and record exactly one sanitized
failure with code, raw SHA, and actual request count.

### F6 — accepted in full

S9 is renamed for the store surface it actually tests. D4 now runs a credential-bearing exhausted
transport through `cli.main` and scans stdout, stderr, and retained text. D5 covers both
`PublishError` and raw `OSError` at the CLI storage boundary. Each case requires named non-zero exit,
no traceback, and removal of bearer value, URL userinfo, query secret, and fragment secret.

### F7 — accepted in full

The real `default_fetcher` is now contracted at its mocked `httpx.get` boundary: exact URL,
header-only bearer, JSON accept header, 60-second timeout, redirects enabled, exact response bytes,
final delivery URL, response metadata, timezone-aware retrieval timestamp, and attempt count. It
must follow the shared `cfbd_http` retry classifier, surface three attempts across timeout/503,
avoid retrying 400/401/403/404/501, exhaust at three, and never expose the key in terminal errors.
The store-level route identity tests then accept only the exact HTTPS provider path/query and reject
foreign, plain-HTTP, look-alike, or swapped deliveries.

## Standing

This artifact requests independent CLEAR only. No GREEN, live paid request, canonical capture,
manifest/catalog change, commit, push, scheduler, cadence input, or consumer wiring has occurred.
