# Realized-outcome manual proof and orphaned-producer install — Codex review

Date: 2026-08-17 (America/New_York)

## Scope and attribution

David ordered two tasks in sequence: manually exercise the realized-outcome scorer, then install weekly scheduling for the two declared freshness producers that had no scheduler. Claude executed the two scorer invocations before Codex completed its preflight. Codex did **not** execute a duplicate scorer run after the deduplication handoff. Codex independently checked the declaration, target resolver, loader counts, schedule/finality, status marker, scorecard absence, plist contracts, installed services, launchd execution, artifacts, and report-freshness evaluation.

## Task 1 — realized-outcome scorer

### Runs and target gate

1. Claude's no-argument scheduled-path reproduction at 2026-08-17 18:08:48Z resolved to season 2025, week 22 and failed `predictions_load_failed:FrozenPredictionSetUndeclared`. The shipped resolver independently returns the same target, and the declaration contains only season 2026. This is the path the Tuesday 10:00 LaunchAgent will take unless repaired or its upstream season resolution changes.
2. Claude's explicit declared-target run at 2026-08-17 18:08:54Z used `--season 2026 --week 1`. It loaded the David-declared 2026-08-05 frozen capture, then terminated `noop / week_not_finalized`, exit 0.

Measured declaration/load substance:

- Declared denominator: 581 predictions.
- Eligible predictions loaded: 501.
- Honest exclusion gap: 80 `capture_incomplete` rows.
- Projection completeness among eligible rows: 501/501.
- Week 1 schedule: 16 games, all `scheduled`, 2026-09-09 through 2026-09-14.
- Corresponding 2026 weekly player-stat provider asset: not yet published (HTTP 404 at the time of the preflight probe).

Terminal marker:

```json
{
  "decision_supported": false,
  "finished_at": "2026-08-17T18:08:54.794531+00:00",
  "noop_reason": "week_not_finalized",
  "season": 2026,
  "status": "noop",
  "week": 1
}
```

Marker SHA-256: `0ca87193614dedcc1de3f3a0a07e9f36e17b02459fe9475ab879cb62a9e0db3f`.

`app/data/realized_outcome/scorecard_latest.json` is absent. Therefore predictions graded = **0** and realized-outcome coverage is **not computable**. Per David's explicit success criterion, this is **not a substantive success**. It proves the declared 2026 frozen prediction loader reaches the finality gate, but it does not prove grading against real outcomes. The exact present wall is `week_not_finalized`; the separate unattended-path defect remains the undeclared 2025/22 resolver target. No repair was attempted.

Focused scorer contracts: 99 passed, 1 pre-existing sklearn pickle-version warning.

## Task 2 — orphaned producers

Declared producers and schedules in `app/config/report_freshness.json`:

- `roster_capacity`: `scripts/run_roster_capacity_audit.py`, weekly 10:00 local.
- `league_opportunity`: `scripts/build_league_opportunity_map.py`, weekly 09:35 local.

Claude authored these plist files; Codex reviewed and installed them under David's direct installation order:

- `ops/launchd/com.davidleess.dynasty-roster-capacity-audit.plist` — Tuesday 10:00, SHA-256 `098bb52bd5f1193a425ac802a18a30319e19fc586a3f28172081d657ef05fbe5`.
- `ops/launchd/com.davidleess.dynasty-league-opportunity-map.plist` — Tuesday 09:35, SHA-256 `bba476406cd47b594114139e44c796fd8417e361959469ba808e655849de1419`.

Repository and installed copies are byte-identical. Both are loaded in `gui/501`, `RunAtLoad=false`, with calendar triggers active. Codex kicked only the still-stale roster-capacity service after installation. It completed with `runs=1`, `last exit code=0`, and no stderr. The opportunity service remains `runs=0` under launchd because Claude's disclosed `--help` mistake had already executed its producer directly and refreshed its artifact; Codex did not duplicate that fire.

Fresh artifacts:

- Roster capacity: `created_at=2026-08-17T18:14:07.804211+00:00`, `status=ok`, `decision_supported=false`, 27 players over 26 slots, one required capacity cut, 21 descriptive candidates, one scenario. SHA-256 `82d60f0f0b2543fccf70affbd599d72e6b10efb8681ce573466dbd64a78df6d1`. Honest gap: 11,485 unrostered-pool rows have unavailable valuation coverage; the emitted recovery range remains unavailable rather than inferred.
- League opportunity: `captured_at=2026-08-17T18:10:14.950004+00:00`, schema `league_opportunity.v2`, 30 descriptive cards, `decision_supported=false`. SHA-256 `ffc8d55eac45df325b49f3d150e8a21b7e2da78ceffb8a16373791f7fb90fe56`.

The production report-freshness evaluator now reports both artifacts `fresh` with basis `embedded_timestamp_fresh`, and preserves `decision_supported=false`. Focused producer/health contracts: 16 passed, 1 pre-existing sklearn pickle-version warning. `plutil -lint` passed for both plists.

No frontend/API/user-facing source was changed. The two repository plist files remain untracked and require an authorized commit if they are to survive a future checkout; the installed LaunchAgent copies are live now.

## Residuals requiring David's decision

- Minimum scorer resolver fix: the unattended path still targets undeclared 2025/22. No fix without David's clearance.
- CLI safety follow-up: `scripts/build_league_opportunity_map.py --help` executes the producer because it has no argument parser. Claude disclosed the unintended fire; no repair was made.
- The paused commit-specific audit of `65b8696` remains separate and has no verdict yet.
