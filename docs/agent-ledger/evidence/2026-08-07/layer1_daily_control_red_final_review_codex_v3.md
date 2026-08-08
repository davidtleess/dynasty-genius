# Layer 1 daily-control RED final review — Codex v3

**Verdict:** NOT CLEAR. The contract is close. Four hard operability gaps remain; they are the
difference between a controller that really ingests data and one that can report success as a no-op.

**Reviewed artifact:** `tests/contract/test_layer1_daily_control_red.py`

**Reviewed SHA-256:** `7033c10dd0b83acc37941a8e9fec8bae9fabc45713b85a1fc965a8ea23d9e975`

**Reproduced:** 39 collected, 38 failed, 1 passing anti-rot registry assertion, zero skips, zero
collection errors; Ruff clean. The one passing standalone registry assertion is appropriate. Change
the module docstring from “Every test must FAIL” to “The suite must remain RED until implementation”
so the text and intended anti-rot pass agree.

## V1 — Exact route triples were requested but only commands are pinned

`PINNED_AUTOMATIC_ROUTES` contains only script paths. The old generic assertion still accepts any
truthy destination and success marker. This directly misses R3's requested command/destination/marker
triples and contradicts the delivery message's “exact entrypoints” framing.

Pin all three fields for each automatic family:

- nflverse: `scripts/run_nflverse_usage_capture.py` → `app/data/nflverse_usage.db` →
  `app/data/nflverse_usage/nflverse_usage_status_latest.json`;
- Sleeper transactions: `scripts/run_league_transaction_capture.py` →
  `app/data/league_transactions.db` →
  `app/data/league_transactions/transaction_capture_status_latest.json`;
- FantasyCalc: `scripts/run_fc_forward_capture.py` → `app/data/fc_forward_capture.db` →
  `app/data/capture/fc_forward_capture_latest_report.json`;
- Sleeper snapshot: `scripts/run_league_snapshot_capture.py` → `app/data/league_runtime` →
  `app/data/league_runtime/capture_status_latest.json`;
- CFBD: `scripts/run_cfbd_foundation_refresh.py` → `app/data/sources/cfbd_foundation` →
  `app/data/sources/cfbd_foundation/status_latest.json`.

The test should compare normalized repo-relative paths exactly and assert the command entrypoint
exists. A nonempty placeholder must fail.

## V2 — No test proves the production runner executes a command

All execution tests inject a fake runner or use `dry_run=True`. GREEN can implement the default
runner as `return SourceResult(... state="executed")` without launching the source command, and the
entire suite passes while no data is ingested.

Patch the module's subprocess boundary and run one selected controller-owned family through the
**default** runner. Assert:

- it receives the exact argv pinned by the manifest;
- `shell=False` (or no shell argument) and a bounded timeout;
- return code zero maps to executed/success;
- nonzero maps to source failure and aggregate nonzero;
- the second independent owned route still runs after the first returns nonzero.

No real network call is needed; this is a mocked subprocess contract.

## V3 — Connection method and PFF assertions are still vacuous

`test_every_entry_declares_a_connection_method` accepts `"x"` for every source. Pin a finite
connection-method ontology and the expected method for every family, derived from the catalog (public
API/library, credentialed paid API, manual download, local static, no sanctioned route, prohibited
scrape, enterprise-gated as applicable). Mode answers whether/how it may execute; connection method
must answer how bytes would be obtained.

`test_pff_route_is_not_overstated` does nothing when `pff.importer` is truthy. Assert it is absent
(or explicitly model only a narrowly scoped existing importer with that scope); the current agreed
state is no whole-source PFF importer, so the simplest honest contract is `pff.importer is None` plus
`missing_importer` status.

PlayerProfiler should use an importer collection explicitly rather than allowing a single long
string containing four commands. Remove the older singular-substring test and assert the collection
equals the four pinned CLI paths.

## V4 — Two selection/read-only edges remain

The forbidden-selection test covers CFBD and FantasyCalc but omits the other externally scheduled
automatic family, Sleeper. Iterate `{"cfbd"} | EXTERNALLY_SCHEDULED` so selection cannot double-pull
either external job.

The named `write_report` guard is useful, but does not by itself prove it is the module's only write
path. Add a preflight test that monkeypatches the relevant `Path.write_text`, `Path.write_bytes`,
`Path.touch`, and replace/rename boundary to raise. Read probes (`exists`, `stat`, `read_text`) remain
available. This proves preflight does not mutate production destinations through a bypass.

## Boundary

No GREEN, source execution, provider contact, paid call, install, commit, or push occurred. Frozen
paths and loose scheduler candidates remain excluded.

H2 QB rushing remains a registered hypothesis UNDER TEST with no result.
