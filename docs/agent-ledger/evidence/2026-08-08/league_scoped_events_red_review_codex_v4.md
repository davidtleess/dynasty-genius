# League-scoped events RED review — Codex v4

**Date:** 2026-08-08 20:22 ET  
**Layer:** Layer 1 ingestion control  
**Reviewed pin:** `b4f741e2f70f389ffaea57cfe777c9758e33828d85b24e42f924ec24a02e52cf`  
**Verdict:** **NOT CLEAR — one isolation blocker**

## Reproduced

- SHA-256 matches.
- Focused pytest true exit `1`: 23 failed, 1 disclosed pass.
- Ruff passes.
- P2 is now satisfiable, P3 covers omitted/explicit/unknown plus a valid scoped declaration, and
  route-incomplete precedence is represented correctly.

## Blocking finding — X1 proves only pre-failure execution

The default manifest order is:

1. `nflverse_usage_capture` — controller-owned automatic
2. `sleeper_transactions` — controller-owned automatic
3–5. other automatic but non-controller/paid routes
6. `playerprofiler` — first manual source
7. `pff`
8–9. incomplete manual routes

Therefore every source added to `ran` executes **before** the malformed manual input is encountered.
X1 would still pass if `execute()` stopped or crashed immediately after recording the first
`manual_inputs_invalid` result: `ran` would already be nonempty and all its earlier results would be
healthy. That does not prove isolation/continuation past a manual fault.

Use an explicit hermetic manifest ordered as:

1. one complete manual source that reaches the malformed scoped input;
2. one synthetic, preflight-valid, controller-owned automatic entry.

Assert the exact runner list equals the later automatic source and that its result has the expected
successful state. This mutation must fail if the controller breaks/returns/raises after the manual
fault. The test should not depend on today's production manifest ordering or route availability.

Also apply the “every declared stream serializes both axes” assertion to route-incomplete manual
sources if X1 continues using the default manifest; its current loop checks both axes only for PFF
and PlayerProfiler while its prose claims every declared stream. A two-entry hermetic test can narrow
that prose to the one manual source and leave the already-shipped route-incomplete contracts as the
separate guard.

## What held

All other repairs in this RED are accepted. No GREEN, governed input, capture, paid call, provider
contact, scheduler, commit or push was authorized or made by this review.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
