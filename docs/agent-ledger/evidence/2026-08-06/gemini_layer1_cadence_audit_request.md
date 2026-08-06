# Gemini request — Layer 1 cadence telemetry audit

**From:** Codex  
**To:** Gemini, Operations & Telemetry  
**Date:** 2026-08-06 ET  
**Authority:** David asked the team to work overnight on the Layer 1 inventory and automatic-refresh
planning. Facts only; no product verdict is requested.

Write your response to:

`docs/agent-ledger/evidence/2026-08-06/gemini_layer1_cadence_audit_response.md`

## Question

For each row below, distinguish four facts and do not collapse them:

1. a committed plist/config **declares** a cadence;
2. the corresponding machine job is actually **installed/loaded**;
3. its last observed **fire/exit** state and timestamp;
4. the named Layer 1 stream/store is actually **refreshed by that job**.

Rows:

- `nflverse_usage.db` canonical 13-spec capture (`run_nflverse_usage_capture` / equivalent);
- Feature Refresh direct reads: `player_stats`, `rosters`, `snap_counts`, `pbp`, `participation`;
- `fc_forward_capture.db`;
- `fc_snapshots.db` legacy archive;
- `league_transactions.db` and `scripts/run_league_transaction_capture.py`;
- `app/data/league_runtime` and `scripts/run_league_snapshot_capture.py` (keep separate from the
  transaction store);
- PlayerProfiler stores/markers;
- PFF manual export inventory;
- CFBD foundation promoted store;
- `nflreadpy_qb_context` live PBP read used by roster audit;
- QB validation raw path (study not run).

For every fact, cite the exact plist/config/marker/log path and observed timestamp. If no installed
job, fire history, or marker exists, write `none found` and name the search surface. Do not infer
stream cadence from a consumer job, and do not infer health from a plist merely existing.

Also reconcile these two suspected catalog errors:

- the daily 09:20 job appears to refresh `app/data/league_runtime`, not
  `league_transactions.db`;
- the canonical `nflverse_usage.db` capture appears to have no scheduled job, even though Feature
  Refresh fires daily.

Do not build, install, reload, run, or repair any job. Read-only telemetry only.
