# League-scoped events RED review — Codex v3

**Date:** 2026-08-08 20:14 ET  
**Layer:** Layer 1 ingestion control  
**Reviewed pin:** `4c3675e40ed1e61eb65ac0ec0949f1aa03a6636fa24d211ce75d40b03b9ade6f`  
**Verdict:** **NOT CLEAR**

## Reproduced

- SHA-256 matches the routed pin.
- Focused pytest true exit `1`: 22 failed, 1 disclosed existing-behavior pass.
- `.venv/bin/ruff check` passes.
- The prior eight repairs are present: topology, exact-state assertions, temporal crossing, scoped
  validation cases, absence-vs-malformation, factual preamble and Ruff cleanup all improved in the
  intended direction.

## Blocking findings

### F1 — P2 is internally unsatisfiable for `playerprofiler.roster`

`EXPECTED_COMPETITION` includes `("playerprofiler", "roster"): "nfl"`, but P2 constructs `actual`
only from policies carrying `game_week_complete` or `season_final`. The shipped roster policy carries
`league_year_open` and `draft_complete`, so it is necessarily excluded from `actual`. A correct GREEN
cannot make the maps equal without wrongly adding a weekly trigger to roster or dropping the pinned
scope.

Define the exact set of competition-scoped calendar triggers consistently. If roster remains in the
pinned map, the selector must include its league-year/draft events (and the player-season combine
event under the same NFL scope). P3b's prose must also stop saying roster should remain unscoped;
that contradicts the map. Medical/operator-drop is the valid unscoped counter-case.

### F2 — P3 tests explicit `None`, not an actually omitted competition field

The raw-declaration defect includes the legacy three-tuple shape. P3 supplies a four-tuple whose
fourth element is `None`; it does not prove a three-tuple game policy fails with
`competition_missing` rather than an unpacking error or silent inference. Parameterize both omitted
arity and explicit `None`, retain the unknown-competition case, and add a valid explicitly scoped
game-policy counter-case. For the non-game counter-case, decide and pin whether the supported raw
shape is a three-tuple or four-tuple with `None`; do not leave the constructor contract ambiguous.

### F3 — X1 conflicts with route-incomplete precedence and does not prove an automatic route ran

The default manual manifest has two complete routes (PlayerProfiler, PFF) and two intentionally
incomplete routes (RotoViz, Campus2Canton). `_manual_result` checks route completeness before cadence
inputs, so the latter correctly remain `manual_route_incomplete`; X1 requires every manual source to
be `manual_inputs_invalid`. The test will therefore fail after the scope repair for the wrong reason.

X1 also creates `ran` but never asserts it. Its `automatic` dict is actually every non-manual result,
including static, blocked and externally scheduled entries. All can be non-failing without the
injected runner executing once, so the claimed isolation proof is vacuous.

Use a hermetic two-entry manifest: one complete manual PFF/PlayerProfiler entry and one synthetic,
preflight-valid controller-owned automatic entry. Assert the manual result is invalid with the exact
scope code; assert every declared manual stream serializes both axes; assert `ran` equals the exact
automatic source and its result is successful. Alternatively preserve the default manifest but
partition complete and incomplete manual routes explicitly and still assert at least one named
automatic runner invocation.

The X1 prose should say both axes remain serialized; a corrupted calendar currently makes coverage
`unknown`, so it does not preserve a substantive coverage answer merely because coverage uses a
valid vocabulary token.

## What held

PFF phantom removal, exact FBS/NFL behavioral isolation, missing-FBS honesty, stable detail-code
prefixes and the corrected season-final timestamp are accepted. No GREEN, capture, governed input,
paid call, provider contact, scheduler, commit or push was authorized or made by this review.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
