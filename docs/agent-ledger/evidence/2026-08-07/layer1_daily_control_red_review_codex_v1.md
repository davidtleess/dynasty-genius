# Layer 1 daily-control RED review — Codex v1

**Verdict:** NOT CLEAR. The suite is genuinely RED, but it encodes several incorrect or
under-specified contracts. Do not write GREEN against this pin.

**Reviewed artifact:** `tests/contract/test_layer1_daily_control_red.py`

**Reviewed SHA-256:** `9d714f389ef98e4d183bfc993173be3daa7a2a5d1ca4216e86d14e7ce9cd647f`

## What is sound

- The missing module yields 18 test failures, zero skips, and zero collection errors.
- The five-mode ontology is correct; `paid_gated` is an execution gate on `automatic`.
- CFBD remains a daily target while paid execution is skipped without failure.
- Independent automatic sources continue after one fails, and aggregate exit is nonzero.
- Manual staleness is an acquisition obligation, not a failed job.
- The controller does not install or replace schedulers in v1.

## Findings

### F1 — Acquisition family and registry definition are conflated

The test requires each `SOURCE_REGISTRY` key to equal exactly one `ManifestEntry.source`, then also
requires `nflverse_usage_capture` as a separate entry. This can force duplicate entries for the same
canonical acquisition route (for example `nfl_nextgen_stats` and `nflverse_usage_capture`) or fake
jobs whose only purpose is satisfying a name test.

Use an acquisition-family identifier for `entry.source` and a `registry_sources` tuple/set for the
registry definitions covered by that family. Flattening all `registry_sources` across the manifest
must equal the registry keys exactly once: no missing alias and no duplicate alias. Families outside
the registry, including Sleeper transactions and the canonical nflverse capture identity, remain
explicit manifest entries.

### F2 — Mode assignments are not pinned

The suite proves only that every entry uses an allowed mode. A vacuous implementation could mark
nearly every source `static`, `blocked`, or `prohibited` and pass while failing David's actual task.

Pin the known critical assignments in the RED. At minimum:

- automatic: FantasyCalc, Sleeper normalized snapshot, Sleeper transactions, canonical nflverse
  capture, and CFBD with `paid_gated=True`;
- manual download: PlayerProfiler, PFF, RotoViz, Campus2Canton;
- blocked: RAS, MFL rookie ADP, Dynasty Data Lab, Dynasty Nerds, plus each registry provenance or
  runnable-route gap the catalog already names;
- prohibited: KTC and the four enterprise providers;
- static: the pinned QB validation study input.

If a registry label is covered by a broader acquisition family, assert the assignment through its
alias rather than creating a second command entry.

### F3 — The manual-importer requirement invents routes

The aligned rule was: a manual entry names drop location and importer **when they exist**, and status
names the exact missing piece when either is absent. The current test instead requires both on every
manual source. That would encourage fabricated importers for RotoViz/Campus2Canton or overstate broad
PFF coverage from its narrow existing consumers.

Allow absent `drop_location` or `importer`; assert `entry_status()` reports `missing_drop_location`
or `missing_importer` precisely. Pin real importers only where the repo proves them.

### F4 — Daily is not meaningful for static/prohibited entries

The current final loop requires `target_cadence == "daily"` for every entry. Daily is the local
default for refreshable acquisition obligations, including automatic, manual-download, blocked, and
paid-gated CFBD. Static and prohibited sources do not have a refresh operation and should carry no
refresh target (`None`), not a fictional daily cadence.

### F5 — Source-text greps do not prove cadence separation or atomicity

Forbidding the strings `source_publish`, `publish_cadence`, and `provider_cadence` prevents comments
or documentation from explaining the boundary and can be bypassed with another name. Assert that no
manifest/report dataclass field or serialized key represents provider-publication cadence.

Likewise, finding `.replace(` in source does not prove the report is atomic. Keep the normal valid
JSON/no-temp-file assertion, and add a behavioral failure test: pre-seed the final report, inject an
atomic-replace failure, and prove the pre-existing final bytes remain unchanged. Because the
aggregate report is v1's canonical status surface, this is proportionate rather than over-building.

### F6 — Preflight can still execute subprocesses

Socket monkeypatches catch direct networking but not an invoked CLI or shell command that performs
network I/O or writes elsewhere. Inject/patch the command runner (or `subprocess.run`/`Popen`) to fail
if called during preflight. Preflight may inspect paths and environment only.

### F7 — Ownership should be declared, with checked-in evidence

Do not derive controller ownership from the current machine's installed plists; that makes CI and
replay depend on mutable host state. Keep ownership explicit. For externally scheduled entries,
record a checked-in scheduler path/job identity and test that the declared path exists. The two
untracked loose candidate plists remain outside v1 and cannot be used as evidence.

Also correct the test name/docstring: it says “three already scheduled jobs” but asserts only
FantasyCalc and Sleeper. Feature Refresh is a distinct existing live-read route, not silently the
third member of that two-item assertion.

### F8 — Manual semantics need full manifest coverage

PlayerProfiler alone does not prove manual-source behavior. For every manual entry, execution must
remain non-failing and non-executing. If a real drop location and timestamp exist, report
`manual_current`/`manual_due` with an age. If the route is incomplete, report the exact missing
drop/import component rather than inventing an age or converting the obligation into job failure.

## Boundaries

No GREEN was written. No source was contacted or executed. No paid call, scheduler installation,
provider email, subscriber-data access, commit, or push occurred. The two loose scheduler candidates
and the frozen wire pair remain excluded.

H2 QB rushing remains a registered hypothesis UNDER TEST with no result.
