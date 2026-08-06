# Gemini handoff — Layer 1 Feature Refresh route

**From:** David and Codex  
**Date:** 2026-08-06 ET  
**Communication mode:** shared-file handoff; no dependency on `dg_delivery.py`

## David's direction

David explicitly asked Gemini to pressure-test the ingestion choice and recommend an option. David
has now stated that he thinks **Option A is better**. Treat that as his disclosed preference, not as
a request to agree with him; preserve any dissent supported by operational evidence.

## Decision under review

The daily Feature Refresh currently reads five nflverse datasets directly into memory:

- `player_stats`
- `rosters`
- `snap_counts`
- `pbp`
- `participation`

**Option A:** make all five governed Layer 1 captured streams and have Feature Refresh consume
content-addressed, last-good local artifacts. No live-provider fallback in the feature job.

**Option B:** retain direct live provider reads as a separately governed ingestion surface. This
would require an explicit amendment to the repository's one-adapter/one-production-route rule.

Claude and Codex independently recommend Option A. Their evidence includes:

- Yesterday's feature refresh is not replayable from the current direct reads; only a combined
  source hash is recorded, not replayable provider bytes.
- A provider timeout can abort an unrelated derivation in the morning critical path.
- `snap_counts` already exists in the canonical store while the job also reads it live, creating two
  routes today.
- For the job's 2018–2025 window, exact source Parquet totals about 189.32 MiB across 1,101,479 rows;
  conditional upstream requests can return HTTP 304 with no body.
- The existing JSON raw-snapshot shape is unsuitable for the large datasets: 129 `snap_counts`
  envelopes occupy about 1.12 GB, roughly 37× the equivalent Parquet bytes.
- The governed backup recovery is still being verified, and the present manifest does not protect
  `app/data/nflverse_usage.db` or its raw tree. Any Option A design must solve retention and backup
  inclusion before enablement.

## Gemini task

Pressure-test both options from an operational/reliability perspective and provide your own
recommendation. At minimum address:

1. Whether any of the five streams should remain a direct live read, and why.
2. Failure isolation, replayability, freshness, upstream revision handling, storage, and backup
   consequences.
3. Whether a per-stream mixture is operationally coherent or merely recreates parallel routes.
4. Preconditions before Option A may be enabled, including backup/retention and freshness markers.
5. Any material disagreement with Claude/Codex or with David's stated preference.

Do not implement, schedule, capture, approve permissions, or change product data. This is a
recommendation only. H2 QB rushing is unrelated and remains **UNDER TEST** with no result.

## Response contract

Write the response to:

`docs/agent-ledger/evidence/2026-08-06/gemini_option_a_pressure_test_response.md`

Include evidence paths and timestamps for operational claims. End with one of:

- `RECOMMENDATION: OPTION A`
- `RECOMMENDATION: OPTION B`
- `RECOMMENDATION: MIXED` followed by the exact per-stream mapping
- `BLOCKED` followed by the missing evidence

