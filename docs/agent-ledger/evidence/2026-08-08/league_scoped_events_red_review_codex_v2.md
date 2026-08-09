# League-scoped events RED review — Codex v2

**Date:** 2026-08-08 20:02 ET  
**Layer:** Layer 1 ingestion control  
**Reviewed pin:** `2cb237b766f4ae05a05ce9aabdbb742894d8c78a48d691f5a17a1a2da08f3bff`  
**Verdict:** **NOT CLEAR**

## Reproduced

- SHA-256 matches the routed pin.
- Focused pytest true exit `1`: 18 failed, 1 passed, zero skips/errors.
- The one pass, P5, is an existing-behavior regression guard and is properly disclosed.
- P4's single outcome is correct: the cadence registry must contain exactly the fourteen real PFF
  league/report lanes and no grades phantom.
- P6 now reads `stream_disposition`, the surface that actually owns the advisory flag, and is not
  the prior vacuous `getattr` check.

## Blocking findings

### F1 — Ruff still fails

`uvx ruff check tests/contract/test_league_scoped_events_red.py` reports three F841 violations at
lines 320, 340 and 359. Each assigns `m = _mod()` and never uses it. The earlier Ruff finding was
not repaired.

### F2 — the competition map is still not total

P2 builds `actual` only by iterating `EXPECTED_COMPETITION`. A GREEN can add an extra game-triggered
policy with any allowed competition and P2 will never see it; P3 then accepts it. Assert equality
against the complete declared scoped-policy surface in both directions, not only lookup correctness
for expected keys.

### F3 — raw unscoped declarations are still not rejected

P3 inspects the assembled registry. It does not prove `build_policy_registry` refuses a raw
game-triggered declaration that omits competition (or names an unknown one). A GREEN could infer a
scope from a stream prefix, accept an unscoped raw declaration, and pass P3. Exercise the public
registry constructor with missing, unknown and valid explicit competition declarations; require an
explicit stable error code for the two invalid cases.

### F4 — validator tests still couple to prose and lack stable codes

V1/V2 use `"competition" in detail.lower()` as proof that the intended guard fired. That remains a
message substring, not a machine contract, and can pass on unrelated prose. Expose or serialize a
stable scope validation code at the pure/public validator surface and assert the code. Keep prose
only as a diagnostic.

### F5 — absent competition evidence is not distinguished from malformed evidence

The valid counter-case always supplies both NFL and FBS blocks. The production sequence deliberately
has NFL/B21 evidence while FBS may be absent. Pin that a missing FBS competition block is valid and
causes FBS streams to report `undetermined`; a present-but-partial FBS block remains invalid. Without
this counter-case, the GREEN can require both competitions and convert honest absence into a
configuration failure.

### F6 — no full-controller fail-closed/isolation test for the new scope guard

All V tests call `_validate_inputs` directly. Pin one malformed scope through the real controller:
nonzero aggregate exit, manual source marked `manual_inputs_invalid`, all declared streams and both
axes serialized, and a later healthy automatic route still executed. Existing generic invalid-input
tests do not prove the new scoped shape reaches that boundary correctly.

### F7 — the behavioral isolation tests are still weak, and I3 does not cross its event

- I1 asserts only `cadence != due`; the exact honest result is `undetermined` with no trigger.
- I2 should assert the exact NFL `undetermined` state as well as FBS `due`.
- I4 asserts only `FBS != not_due`, allowing the wrong `current` or `due`; with no FBS completions,
  the exact result is `undetermined`.
- I3 evaluates at `2027-01-05T00:00Z`, but the NFL final is
  `2027-01-04T20:20-05:00` = `2027-01-05T01:20Z`. The test runs 80 minutes before the NFL final and
  therefore never exercises the season-final leak it claims to reproduce. Move `now` after the NFL
  final but before the FBS final and assert the exact FBS state/trigger.

### F8 — the module-absence preamble remains false

The file still says the scoped module does not exist. `feed_cadence.py` exists; the scoped behavior
does not. Correct the factual preamble before repinning.

## What held

The PFF topology correction and the FBS current-not-permanent correction are accepted. The shipped
manual-feed contract may be amended in GREEN once this RED is clear. No paid CFBD call, capture,
scheduler, provider contact, production artifact, code edit, commit or push was authorized or made
by this review.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
