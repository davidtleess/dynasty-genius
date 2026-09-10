# Resume delayed feeds without losing available data

David's September10 goal: late snap counts should not stop ingestion; check what is available, ingest missing or changed partitions, and continue independent tasks.

Existing StreamSpec/UsageStore are the capture owners. The6:15 usage collector is separate from the9AM ChainStep graph. Feature refresh already isolates its five core loaders and refuses unauthorized season-basis changes. This bounded increment fixes usage acquisition and delayed-feed retries; it does not add duplicate box-score adapters or rebase the model.

## Ownership
- DG215 / actual Claude54410: canonical incremental capture, CLI, partition state and provenance.
- DG216 / actual Claude54281: existing guard retry integration, relevant operational state, single scheduler ownership.
- Root DG214: integrate source changes from both isolated worktrees, verify current feeds and data/model preservation, real-source/fault rehearsal and handoff.
- Actual Claude54331: independent architecture and final code/evidence review, read-only builder trees.

## Contract to agree before code
Prefer a small additive retry object in the existing capture status: schema_version, next_retry_at in UTC, and due partitions with explicit reason/attempt identity. Missing is waiting, not zero. Completed seasonal source content is idempotent; an upstream correction is a new revision. A retry-only CLI mode reads canonical state and only checks due partitions; it must not recapture snapshot-axis feeds or trigger the model. Guard reuses the installed15minute ticks, rate-limits to hourly per delayed partition, and must not turn a malformed receipt or deterministic failure into an automatic retry. Builders may refine field names together, record final contract here via root, and keep backward compatibility. No installed plist changes required.

Source errors remain visible and nonzero; continue independent partitions when safe. Known unavailable current-season releases can wait. Preserve last good rows and their observation times. Export readiness cannot assert fresh data for a waiting/failed partition. Snapshot-axis accumulation stays intact. Core feature required-input and season-basis checks remain unchanged.

## Implementation and evidence sequence
1. Read current code and record failing tests for late snap feed, following healthy feed, empty response, unchanged retry, late arrival, correction, real failure, due retry guard and overlapping attempts.
2. Implement bounded capture and retry changes in disjoint builder ownership.
3. Integrate patches in DG214, run the relevant full capture/ops/dependency/source-basis regression set and static checks.
4. Independent reviewer checks code and run receipts; fix material findings.
5. Isolated live-source rehearsal with explicit DB/raw/export/cache paths under a new run: available feed succeeds while actual2026snaps absence waits, no shared producer or DB writes. Synthetic fault/restart tests cover arrivals/corrections not yet observed upstream. Frontend is unchanged, so pipeline artifacts/CLI are the real surface.
6. Record final changes, pass/fail evidence, limits, and exact proposed production activation. Preserve DG213 and all original artifacts.

## Agreed builder contract (September10)
The capture status adds `partitions` with full state and optional `retry` object (`schema_version: capture.retry.v1`, aware-UTC `next_retry_at`, nullable `in_flight`, and `due`). Each due entry declares partition, stream, season, reason, retryable=true, attempt count/id and last_attempt_at. The due list contains capture-confirmed waiting/interrupted attempts and explicit current-season revision checks. Available data remains available during a revision check. Deterministic failures stay visible as error and never auto-retry. Retry-only retains all untouched partition state. CLI: `run_nflverse_usage_capture.py --retry-only` with explicit --db-path/--raw-root/--export-root for isolation. Exit0 includes waiting;1 actual failure;3 lock held/noattempt. Before-min-season is a permanent structural exclusion, never an hourly retry.

Root review corrections: real missing2026snap asset must be recognized through its declared canonical URL and corroborating official release inventory; arbitrary404 stays an error. Empty expected current-season game data must wait rather than erase facts. Recover process death through advisory locks on canonical DB path/persistent inode, not stale-file unlinking; test aliases and SIGKILL recovery. The retired daily_control runner stays retired.

## Ongoing-season acceptance refinement
Checking only absent/empty season files would fix kickoff but fail later: a nonempty current-season file can still lack the newest game. Successful current-season seasonal partitions therefore also receive bounded hourly revision checks through the same guard and due-selection contract, with an explicit revision-check reason. Available data remains available; a scheduled recheck does not mean missing data. Exclude snapshots, archives, structural exclusions and actual errors from this hourly policy. Reuse unchanged content and ingest provider corrections/additions. Test a nonempty week1 payload followed by a delayed week2 addition. Season-level source availability never claims every completed game is covered; models retain their own required-input/basis checks. No new framework, adapter, service or production activation.

## Final verification boundaries
Root checks the actual capture CLI in child processes, with provider transport and time controlled: both full and retry entrypoints must obtain release-inventory evidence for an absent asset; guard partition narrowing must survive the process boundary; unchanged content remains unchanged and a later game addition is stored. A separate live rehearsal retrieves the real current-season snap asset and latest-date depth-chart slice into a pristine private store, with shared cache disabled. Neither evidence claims game-complete coverage or a refreshed model.

Normalization failures are isolated source-data errors; store or coherent-publication failures remain fatal. Last good facts remain intact and failed/interrupted inputs cannot claim readiness. Initial and per-partition running markers preserve the retry queue. An empty or legacy retry receipt performs no capture; a normal capture is needed to establish current partition state.

Production activation remains a separate gate under David's shared-data/production boundary. Land through dg-land.sh, verify no old capture/guard writer is active before switching lock protocols, and use one ordinary production capture to seed the additive retry metadata (or wait for the next scheduled daily capture). Existing installed schedules need no reload. Do not manually run producers during the 09:00–10:15 Eastern protected window. Check resulting receipts and the next due guard tick; do not restart the API, retrain, or change the model season basis.
