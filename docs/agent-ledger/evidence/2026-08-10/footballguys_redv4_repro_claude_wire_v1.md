From Claude Code (implementing lane) — RED v4 REPRODUCED EXACTLY; GREEN repair begins now

RED pin `45d7e6f4cd865d55ed024c1829dbd0c0f9f1b6ab77cfa3b1554a94493ce7966e` (2,038 lines) and
record pin `189ddf7f…` both reproduce byte-exact. Exact strict command against unmodified GREEN
`c5d87c62…`: **222 collected = 17 failed + 205 passed, process exit 1** — identical census,
identical failure identities (verified through s31/s32 tails). Baseline GREEN hash unchanged.

Repairing against this exact file now: migration/versioning first (C1), then the governed
evidence + adjudication store (C2), derived readiness (H3), attempt ordering (H4), special
composition (H5), sidecar columns (H6), 0444 (M7), header pin (M9). Will report
222/222 under `-W error` exit 0 + full-suite census + ruff before any landing word.
No commit/push/capture until David's word; pair travels together. H2 remains UNDER TEST.
