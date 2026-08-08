# Layer 1 daily-control RED re-review — Codex v2

**Verdict:** NOT CLEAR. F1–F8 were accepted and substantially repaired. Six bounded residuals remain;
all are about making the controller actually operate the correct routes, not about presentation.

**Reviewed artifact:** `tests/contract/test_layer1_daily_control_red.py`

**Reviewed SHA-256:** `fe9928463bd26dcb63f70b71063c1d26e9a7e462c960a64d2950c43c9e33420c`

**Reproduced RED:** 28 failed, zero skipped, zero collection errors.

## R1 — Full registry ownership/mode mapping is still unpinned

`PINNED_MODES` covers 9 acquisition families, but the registry has 20 definitions. The partition
test proves only that every registry key appears somewhere; it does not prove the correct family owns
it. GREEN could put `rotoviz`, `campus2canton`, all four enterprise providers, the QB validation
input, and every remaining blocked source under arbitrary families/modes and still pass.

Pin the complete registry-owner mapping and mode state, not only a sample. The evidence-backed shape
is:

- `nflverse_usage_capture` owns registry aliases `nfl_nextgen_stats` and
  `nflreadpy_qb_context` and is `automatic`;
- `nfl_data_py` remains its own `blocked` provenance-gap family rather than being laundered into the
  canonical nflverse route;
- `cfbd`, `fantasycalc`, and `sleeper` are `automatic`;
- `playerprofiler`, `pff`, `rotoviz`, and `campus2canton` are `manual_download`;
- `ras`, `mfl_rookie_adp`, `dynasty_data_lab`, and `dynasty_nerds` are `blocked`;
- `ktc`, `sportradar`, `genius_sports`, `stats_perform`, and `rolling_insights` are `prohibited`;
- `nflreadpy_qb_validation` is `static`;
- `sleeper_transactions` is an automatic family outside the registry.

This is 20 registry keys exactly once plus the extra transactions family. If the implementer finds
repo evidence that breaks one ownership assignment, that is a genuine fork to route rather than an
arbitrary GREEN choice.

## R2 — Execution is not constrained to controller-owned sources

The suite asserts `controller_owned` metadata, but never asserts that `execute()` obeys it. An
implementation can call the runner for FantasyCalc and Sleeper as well as the two controller-owned
routes, double-pull both existing jobs, and still pass every current test.

Inject a recording runner and assert the default called set is exactly
`{"nflverse_usage_capture", "sleeper_transactions"}`. CFBD must be skipped by its paid gate;
externally scheduled automatic families must be accounted for but not invoked. Also assert an
explicit source selection can run one controller-owned family without running the other, because
that was part of F-A alignment.

## R3 — Truthy placeholders can satisfy every route contract

The automatic-entry test accepts any nonempty command, destination, and marker (`"x"` passes). The
task is to determine how every source connects, ingests, and refreshes, so the critical runnable
routes must be pinned to actual repo entrypoints and destinations:

- nflverse: `scripts/run_nflverse_usage_capture.py` → `app/data/nflverse_usage.db` →
  `app/data/nflverse_usage/nflverse_usage_status_latest.json`;
- Sleeper transactions: `scripts/run_league_transaction_capture.py` →
  `app/data/league_transactions.db` →
  `app/data/league_transactions/transaction_capture_status_latest.json`;
- FantasyCalc: `scripts/run_fc_forward_capture.py` → `app/data/fc_forward_capture.db` →
  `app/data/capture/fc_forward_capture_latest_report.json`;
- Sleeper normalized snapshot: `scripts/run_league_snapshot_capture.py` →
  `app/data/league_runtime` → `app/data/league_runtime/capture_status_latest.json`;
- CFBD: `scripts/run_cfbd_foundation_refresh.py` → `app/data/sources/cfbd_foundation` →
  `app/data/sources/cfbd_foundation/status_latest.json`.

Assert each command exists and pin those values. The manifest also needs an explicit connection
method/gate or route state for every family; mode alone does not answer “how to connect.”

PlayerProfiler is not one importer: its five report families are covered by four checked-in CLIs
(`run_playerprofiler_ingest.py`, `run_playerprofiler_roster_ingest.py`,
`run_playerprofiler_gamelog_ingest.py`, `run_playerprofiler_pbp_ingest.py`). Represent importers as a
collection and pin all four. Do not overstate PFF's narrow existing consumers as a whole-source
importer.

## R4 — The canonical report path and freshness contract are absent

The tests accept any JSON filename and do not require automatic/static/blocked/prohibited results to
carry the planned `last_success` and staleness state. A timestamped random filename would pass while
giving operators no stable status surface.

Pin one stable report filename/path under the supplied `report_root`, and require every source result
to include `checked_at`, nullable `last_success_at`, and an honest staleness/due state derived from
its success marker or missing route. Manual `age_days` remains as already tested. Unknown is a valid
state; omission is not.

## R5 — Preflight is not yet proved read-only

Snapshotting only `report_root` does not detect writes to the real destinations or elsewhere in the
repo. The no-subprocess and no-socket guards are good, but the read-only claim still outruns its
test.

Patch the module's governed write helper(s), plus common path write/mutation calls used by this
module, to raise if preflight invokes them; or inject a write function and prove it is never called.
The contract should be architectural: preflight receives/uses read-only probes and has no writer.

## R6 — Two source-text/substr checks recreate the proxy problem

`test_manifest_entry_exposes_no_installed_host_state` greps only for the word `LaunchAgents`. It
both forbids harmless explanatory prose and misses `launchctl`, another home path, or any other host
probe. Remove it. Declared ownership plus exact checked-in scheduler paths is the deterministic
contract; pin the FantasyCalc and Sleeper plist paths exactly and assert they exist.

The serialized-cadence test says “banned KEY” but scans the whole JSON string. Recursively collect
dictionary keys and compare those; a caveat value explaining that publication cadence is out of
scope must not fail. Likewise use `dataclasses.fields()` rather than `vars()` so the contract does
not unnecessarily forbid a slotted immutable dataclass.

## Boundary

No GREEN, source execution, provider contact, paid call, install, commit, or push occurred. Frozen
paths and loose scheduler candidates remain excluded.

H2 QB rushing remains a registered hypothesis UNDER TEST with no result.
