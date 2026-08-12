# Footballguys direct semantic-state clock probe — Codex v1

Date: 2026-08-12  
Layer: 1 — governed semantic evidence read boundary

This probe ran while RED v23 was frozen; it did not edit that contract and is queued for the next
adversarial round.

## Reproductions against GREEN v22 `b0bf23ac…`

1. Write one valid provider-authentic horizon assertion. Replace the driver's clock with a
   callable raising `RuntimeError("clock down")`. Call the public `semantic_state(...)` seam.
   **Observed:** bare `RuntimeError` escapes.
2. Write the same valid assertion, then simulate a restored/corrupt future attachment by changing
   its persisted retrieval instant to `2099-01-01T00:00:00Z`. Replace the clock with
   `lambda: None`. Call `semantic_state(...)`.
   **Observed:** the state is `known`, `value=redraft`, and `eligible_for_phase_c=true`.

## Cause and required next boundary

`semantic_state` calls `_now()` inside attachment reduction without first validating and pinning
one read clock. A failing dependency leaks. A `None` dependency becomes `_canonical_instant(...,
now=None)`, disabling the future guard exactly as the v22 write-side defect did. Multiple
attachments also cause multiple clock samples, so one reduction need not share one time basis.

The next RED should require the direct semantic-state seam to validate and pin one aware,
whole-second clock before reduction; invalid values or ordinary dependency exceptions yield a
named fail-closed unknown state; future restored evidence stays ineligible; and a counted/changing
clock is observed exactly once. `read_model`'s already-pinned clock must be reused rather than
sampled again.

No commit, push, capture, provider contact, scheduler, or Phase B/C/D. H2 QB rushing remains
**UNDER TEST** and unrelated.
