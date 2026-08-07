# Legacy enrichment retirement — GREEN CLEAR (Codex v5)

**Date:** 2026-08-07 ET  
**Layer:** Layer 1 ingestion  
**Verdict:** **GREEN CLEAR**  
**Scope:** retirement of the executable mixed PlayerProfiler/CFBD legacy enrichment route and extraction of its leakage guard. This is not commit or push authority.

## Reviewed target

Claude reproduced the unchanged RED before implementation: **6 failed / 1 passed** at
`tests/contract/test_legacy_enrichment_route_retirement_red.py`, SHA-256
`e9062793cbdcc95446436152ec31f2f564d857c822bdfbd115382d4f5c2840c9`.
The RED remains byte-identical after GREEN.

The GREEN retires both tracked legacy PlayerProfiler HTTP scripts:

- `scripts/enrich_training_data.py` — deleted;
- `scripts/probe_playerprofiler.py` — deleted under David's explicit deletion word.

It preserves the governed acquisition entrypoints `scripts/run_cfbd_foundation_refresh.py` and
`scripts/run_playerprofiler_ingest.py`.

## Cleared pins

- `src/dynasty_genius/models/leakage.py` —
  `ef0497c6e5fa40f3546d8ece667a180591526396a52528ba2632658e18f62088`
- `tests/test_leakage_scanner.py` —
  `c9e023adff1b23b92bca4687eaa7452ea5a818f2d22b74042de6abfcca5fca89`
- `tests/test_engine_a_backtest.py` —
  `23f7b3970cad71e46e54ad3e9cb06035599dc8b9b0c63e5e8aab5d38a41ccef7`
- `tests/test_engine_a_v2_feature_contract.py` —
  `740c7ace6f6a27755f8cd966b216955412ac84d99d26f40b3a0baa4b8bd84b0d`
- `tests/test_playerprofiler_decision_gate.py` —
  `da93a391dadd037846a9cbf6100ddcc649c3dfc0d6d6191d772ce5360d8fd4d6`
- `tests/contract/test_harness_trust_w1_leakage.py` —
  `c46e0d26aecf2d827f7aa45aabd2ac1d524dc2f608c4a1ceeb4aa6d68b2c16e4`

## Independent review findings

1. **Required `report_path` is correct and within scope.** The RED requires an explicit diagnostic destination. Making it keyword-only and required prevents the old fixed-path overwrite and leaves no compatibility burden because every surviving caller is updated. A clean frame writes nothing; a failing frame writes the diagnostic before raising.
2. **“No replacement enrichment producer exists yet” is honest.** The GREEN correctly names the governed CFBD acquisition route without inventing a producer for the retired combined `v2` artifact. A follow-up ticket is not required to make this retirement safe or truthful.
3. **Removing the retired script from the harness subject tuple is correct.** The path no longer exists, so retaining it would not protect an active surface. The extracted leakage module is covered directly by the retirement RED and leakage unit tests; the harness still covers the live model subjects.
4. Whole-repo executable-path searches found no surviving import or reference to the retired script outside the RED's absence assertions. The only surviving `admin-ajax` mentions are historical/non-executable records, not a runnable provider route.
5. The parked wire files remain outside scope and retain their frozen hashes:
   `scripts/dg_delivery.py` `b3247ec8...`; `tests/contract/test_wire_health_profile_refresh_red.py` `fd924eb1...`.

## Independent gates

- Retirement RED plus focused leakage/decision/harness/Engine A slices: **40 passed / 1 skipped**.
- Full suite: **4,689 passed / 12 skipped / 9 xfailed / 0 failed**, 361 warnings, 375.57s.
- Ruff over every changed production/test path: **PASS**.
- `scripts/validate_governance.py`: **PASS**.
- `git diff --check` and cached-diff check: **clean**.
- RED and all six GREEN pins recomputed independently: **MATCH**.

## Boundary

This CLEAR certifies only the reviewed bytes and the two named deletions. It grants no commit, push,
provider access, catalog edit, checkbox movement, new enrichment producer, capture, scheduler, or
consumer migration. A-C remains open on the two source clocks. H2 QB rushing remains a registered
hypothesis **UNDER TEST** with no result.
