# League-scoped events RED CLEAR — Codex v1

**Date:** 2026-08-08 20:30 ET  
**Layer:** Layer 1 ingestion control  
**Cleared pin:** `94f7edf275360c5e568ee93a505042b09cdd6d16804ae84520eea1788f7d1fe8`  
**Verdict:** **RED CLEAR — proceed to bounded GREEN**

## Independent verification

- SHA-256 recomputed and matched.
- Focused RED: true pytest exit `1`, 23 failed and 2 disclosed passes (P5 and X1b), zero
  skips/errors.
- Ruff: `All checks passed!`.
- Combined with the shipped manual-feed cadence contract: 23 failed / 43 passed. The 43 passes are
  the existing 41 plus the two disclosed regression guards; no shipped cadence regression exists.

## Why the final isolation repair is sufficient

X1 now supplies an explicit two-entry manifest ordered complete manual source first and
preflight-valid automatic source second. It asserts the order, the manual fail-closed result and
both serialized axes, then requires the exact later runner call
`["nflverse_usage_capture"]` and its successful result. A controller that stops after the manual
fault cannot satisfy that assertion. X1b separately preserves the intentional route-incomplete
precedence for RotoViz and Campus2Canton.

## Cleared GREEN scope

Implement only the contracts in the cleared RED:

- explicit NFL/FBS competition scope for game-triggered policies;
- raw registry rejection for omitted/`None`/unknown game competition with stable error codes;
- competition-scoped kickoff/final/completion facts, absent evidence remaining honest and malformed
  evidence failing closed;
- bidirectional behavioral isolation and exact states;
- removal of the phantom PFF grades stream while preserving all fourteen real lanes, raw retention,
  ingestion authorization and the independently enforced column-level model-input ban;
- shipped `test_manual_feed_cadence_red.py` amendment required by that factual topology correction;
- daily-controller scope validation and source isolation.

GREEN does not authorize a governed input artifact, B21 or CFBD capture, paid call, provider contact,
scheduler change, source run, commit or push. Return pins and unmasked focused/full gates for review.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
