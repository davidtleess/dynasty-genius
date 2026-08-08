# Layer 1 daily-control RED residual review — Codex v4

Date: 2026-08-07 ET  
Layer: Layer 1  
Candidate reviewed: `tests/contract/test_layer1_daily_control_red.py`  
Candidate SHA-256: `62cd5a96ca561acb5a840b87d7443d123a339cceb876818ce0a3e0a16afdef25`

## R1 — PlayerProfiler importer requirements are mutually incompatible

`test_playerprofiler_names_its_real_importer` requires the expression
`"run_playerprofiler" in pp.importer` to be true. The later
`test_playerprofiler_importers_are_an_explicit_collection_of_the_four_clis` requires `pp.importer`
to be a list or tuple whose string elements are exactly the four full CLI paths in
`PINNED_PLAYERPROFILER_IMPORTERS`. For that exact tuple, membership of the distinct string
`"run_playerprofiler"` is false. Adding that string would violate the exact-set assertion. No GREEN
can satisfy both tests. Remove the stale singular-importer test; retain the exact four-CLI test.

## R2 — connection-method ownership is pinned for only 7 of 21 families

`PINNED_CONNECTION_METHODS` names only nflverse usage capture, Sleeper snapshot, Sleeper
transactions, FantasyCalc, CFBD, PlayerProfiler, and PFF. The test validates only that every other
family uses *some* member of the legal ontology. It does not pin the correct connection method for
RotoViz, Campus2Canton, the five blocked families, five prohibited families, or the static family.
That leaves the Layer 1 connect-method inventory materially under-specified while the test name says
it is pinned per family. Define an evidence-backed method for every family and assert that the map's
keys equal the manifest-family keys.

No Gemini fork exists: these are internal test facts, not a policy disagreement. No GREEN is clear
until both are repaired.

QB rushing remains a registered hypothesis under test with no result.
