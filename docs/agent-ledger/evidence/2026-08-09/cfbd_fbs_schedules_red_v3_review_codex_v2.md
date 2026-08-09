# CFBD FBS schedules RED v3 — independent residual review

Date: 2026-08-09  
Layer: 1 — source capture and retained provenance  
Reviewer: Codex  
Verdict: **NOT CLEAR**

## Reviewed pin and checks

- `tests/contract/test_cfbd_fbs_schedules_capture_red.py`, 1,405 lines:
  `ca8ab632afe34dcd34d01913df17837892eeb10ac69839452b98f3f3b19c6396`
- Independently recomputed the pin.
- Focused RED: **168 failed / 1 disclosed pass** in 16.23s, zero setup or collection errors.
- Ruff: **clean**.
- F1-F7 are accepted as repaired. Two residuals remain.

## Consolidated residual findings

### R1 — the season-type rules contradict each other, and the positive domain exceeds the requested offering

`test_g4aa_every_openapi_season_type_enum_is_accepted` requires `both` to publish successfully
(`test_cfbd_fbs_schedules_capture_red.py:793-801`). The retrieved-failure audit then mutates the same
field to `both` and requires `enum_invalid` (`:1090-1097`, `:1127-1128`). No implementation can satisfy
both contracts.

The wider positive list also admits `allstar`, `spring_regular`, and `spring_postseason` into an
offering explicitly requested as `seasonType=both`. The OpenAPI reuses one broad enum for both query
and response (`openapi.json:6886-6895`), but provider examples use `both` to fetch the normal season
plus bowl/postseason games; it is a filter choice, not evidence that a returned game's season type is
literally `both` or that spring/all-star schedules belong in this FBS offering.

Repair: define the response scope for this route as `regular|postseason`, keep positive controls for
both, and reject `both`, `allstar`, `spring_regular`, and `spring_postseason` as
`season_type_scope_mismatch` (or one equally specific code). The audit matrix must use the same rule.
If the lane instead intends to capture all six response types, then change the query/offering name and
remove the contradictory failure case; do not silently widen this ticket.

### R2 — duplicate JSON member names can silently destroy raw values during canonicalization

The contract rejects duplicate game IDs after `json.loads`, but it never rejects duplicate member names
inside a Game or nested `playoff`. Python's default decoder keeps only the last value. A raw object such
as `{"id":401752001,"id":999,...}` therefore loses a provider value before canonical storage while
still being capable of passing field membership, type, and ID uniqueness checks. That falsifies F1's
claim that every source key and value survives canonicalization.

RFC 8259 defines objects as unordered name/value collections and says names should be unique because
duplicate behavior is unpredictable across implementations. For an evidence store, silent last-value
wins is not acceptable. See [RFC 8259 section 4](https://www.rfc-editor.org/rfc/rfc8259#section-4).

Repair: parse with duplicate-name detection at every object depth and fail closed before canonical
publication. Add top-level Game and nested `playoff` duplicate-member mutants, require exact-byte
quarantine plus the normal sanitized failed-audit record, and give the refusal a specific stable code.

## Disposition

**NOT CLEAR** on `ca8ab632…`. Return one revised pin covering R1-R2; do not start GREEN yet.

