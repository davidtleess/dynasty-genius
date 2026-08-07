# Legacy mixed enrichment route — RED handoff

**Author:** Codex, independent RED lane  
**Layer:** Layer 1 ingestion  
**RED:** `tests/contract/test_legacy_enrichment_route_retirement_red.py`  
**RED SHA-256:** `e9062793cbdcc95446436152ec31f2f564d857c822bdfbd115382d4f5c2840c9`

## Target state

Retire `scripts/enrich_training_data.py` rather than partially removing `PPClient`. The script is a
bypassable mixed-source acquisition route: it performs unsanctioned PlayerProfiler HTTP access,
direct CFBD HTTP access, and publication of the historical `prospects_with_outcomes_v2.csv`
artifact. It has no runtime importer; its remaining dependencies are a leakage test and stale test
instructions.

Preserve the two governed source boundaries:

- CFBD raw-to-curated acquisition:
  `scripts/run_cfbd_foundation_refresh.py` →
  `src.dynasty_genius.capture.cfbd_foundation_refresh` →
  `app/data/sources/cfbd_foundation/`.
- PlayerProfiler acquisition: manual subscriber exports through
  `scripts/run_playerprofiler_ingest.py`.

Move `check_leakage` to `src/dynasty_genius/models/leakage.py`. The extracted function must accept
an explicit `report_path`, remain network-free, accept clean frames, and refuse prohibited columns
while writing a diagnostic.

## Controls

1. The legacy mixed acquisition entrypoint no longer exists.
2. No executable script contains a PlayerProfiler HTTP route.
3. The leakage guard exists in a neutral module with no network-client dependency or provider URL.
4. The extracted guard preserves fail-closed behavior and explicit diagnostic output.
5. Tests no longer import or instruct users to run the retired script.
6. No script combines PlayerProfiler HTTP acquisition with `v2` artifact publication.
7. Positive control: the governed CFBD wrapper and manual PlayerProfiler entrypoint remain present.

## RED result

Command:

```text
.venv/bin/python3.14 -m pytest -q tests/contract/test_legacy_enrichment_route_retirement_red.py
```

Result: **6 failed / 1 passed**, zero collection errors.

Target-specific failures:

- legacy script still exists;
- PlayerProfiler HTTP route remains in that script;
- governed leakage module does not exist;
- extracted leakage behavior is unavailable;
- ten test references/imports still name the legacy script; and
- the legacy script still combines PP HTTP access with `v2` publication.

The positive source-boundary control passes. Ruff on the RED passes and `git diff --check` is clean.

## GREEN boundary

- No network probe.
- Do not run either legacy PlayerProfiler route.
- Do not silently change the contents of an existing `v2` artifact.
- Historical docs may retain the retired script name as history; live test instructions may not.
- Claude owns GREEN; the RED file remains byte-untouched during implementation.
- Commit and push remain separate authority.
- No catalog checkbox moves from this cleanup; A-C remains open on clock evidence.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result.
