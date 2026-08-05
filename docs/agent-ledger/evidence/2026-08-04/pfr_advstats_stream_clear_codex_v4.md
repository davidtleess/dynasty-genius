# PFR advanced-stats — stream CLEAR with live-landing condition

**Reviewer:** Codex  
**Date:** 2026-08-04  
**Layer:** Layer 1 ingestion  
**Disposition:** **CLEAR for batch stream 1 (`load_pfr_advstats`).** Code, contract, staging proof,
and the S1–S7 closure are adequate. GREEN is complete. Live product landing is cleared only under
the isolation condition below.

## Evidence accepted

- Four PFR specs, each bound to `nflreadpy.load_pfr_advstats`, with explicit `stat_type`, distinct
  table, grain `(game_id, pfr_player_id)`, PFR identity, declared numeric types, opt-in non-finite
  refusal, and one exact-shape `StreamEra`.
- The single-era choice is sound. It exercises the adapter's existing exact-column-set refusal for
  PFR while leaving every existing non-era stream unchanged; no global invariant extension is
  required for this landing.
- Raw SHA-256 is computed from the written pre-parse snapshot bytes and recorded for every
  stream-season result.
- S1–S7 are closed in the test/generator/matrix surfaces, including all-five-table preservation,
  in-publisher export failure, exact runtime non-null reconciliation, checked manifests, and corrected
  consumer-scanner positive-control count.
- Codex independently reproduced: 31/31 focused tests; generator `ALL ARTIFACTS MATCH SOURCE`; Ruff
  clean; `git diff --check` clean.
- Implementing-lane full gate: 4,464 passed, 12 skipped, 9 xfailed, zero failures.
- Implementing-lane live staging proof: 121,954 rows = 5,424 pass + 18,461 rush + 35,724 rec +
  62,345 def; identity 121,688 canonical + 266 source-only + zero conflict + zero unknown; typed PFR
  Parquet; raw hashes on all 32 stream-season results. These totals exactly match Codex's independent
  pre-implementation census.

## Live-landing condition

A **PFR-only** capture must not publish to the current canonical NGS export root. The current consumer
silently skips missing NGS manifest entries (`nflverse_usage.py:1544-1547`), so replacing that ready
marker with a PFR-only manifest would make `run_feature_refresh.py` and
`assemble_engine_b_dataset.py` proceed without NGS.

The minimal cleared landing is:

1. Write the four PFR tables into the product SQLite store using only the four PFR specs.
2. Use a dedicated PFR raw/status/export root, not `DEFAULT_RAW_ROOT` / `DEFAULT_EXPORT_ROOT`.
3. Before and after, prove the existing canonical NGS ready marker and every file/hash/row count it
   references are byte-identical.
4. Prove all five existing SQLite data-table fingerprints remain unchanged.
5. Require the landed PFR result to reproduce 121,954 total rows, the four per-type counts, the
   121,688/266/0/0 identity census, 32 matching raw hashes, and a verified four-stream PFR export
   manifest.

An alternative unified landing through the canonical export root must run and publish all nine specs
and prove the manifest contains all nine complete files. That refreshes the existing five upstream
streams and is a materially broader operation; it remains conditional on David's explicit choice.

This CLEAR lands a `substrate_only` stream. It authorizes no consumer, model use, predictive claim,
scheduler, commit, push, merge, or completion claim for the six-stream batch.
