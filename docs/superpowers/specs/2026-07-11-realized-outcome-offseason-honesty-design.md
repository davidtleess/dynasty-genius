# Realized-Outcome Scorer: Off-Season Honesty + FD-Leak Fix

- **Date:** 2026-07-11
- **Status:** DRAFT v2 — round-1 findings integrated (Codex R1–R4 NOT-CLEAR items + Gemini no-concerns); awaiting cockpit CLEAR, then David-authorized RED (standing word given 2026-07-11, conditional on convergence)
- **Authoring lane:** Claude spec · Codex RED · Gemini advisory (framing integrated, two corrections accepted 2026-07-11)
- **Scope:** the weekly realized-outcome scoring job (`scripts/run_realized_outcome_scoring.py` + `src/dynasty_genius/capture/outcome_forward_capture_store.py` connection lifecycle) and its new terminal status marker. It is NOT a change to the scorer math (`realized_outcome_scorer.score`), the frozen-prediction stores, the `/api/realized-outcome` route contract, or capture-health registration (named follow-ups, §3).

## 1. Problem (measured, not inferred)

The weekly Tuesday scorer (`com.davidleess.dynasty-realized-outcome-scoring`, 10:00) has crashed on both fires since go-live instead of performing the designed off-season no-op — and the crash is the only thing preventing a dishonest artifact. Nothing surfaces the failure: there is no status marker, and the absent scorecard reads as healthy-inactive on the API (PR #104 shape).

**Evidence (real runs):** `app/data/logs/realized_outcome_scoring.err.log` (last write Tue 2026-07-07 10:00) holds two identical crash pairs (Jun 30 + Jul 7):

```
File ".../scripts/run_realized_outcome_scoring.py", line 111, in _build_outcomes
File ".../src/dynasty_genius/capture/outcome_forward_capture_store.py", line 303, in read_outcomes
sqlite3.OperationalError: unable to open database file
...
OSError: [Errno 24] Too many open files: '/var/folders/.../T/tmpnu4vh0ap'
```

`launchctl list` shows `LastExitStatus=1` for the agent.

### Root causes (three defects)

**D1 — the off-season no-op assumption is false** (`scripts/run_realized_outcome_scoring.py:235-249`). The resolver docstring claims "Off-season the current week sits past the played weeks, so the week's finality gate yields the honest no-op." nflreadpy's convention keeps returning the COMPLETED season until the new one starts, and its current week is the last playoff week — which is finalized. The gate passes and a full 22-week scoring run is attempted every Tuesday.

**Reproduced:**
```
$ .venv/bin/python3.14 -c "import nflreadpy as nfl; print(int(nfl.get_current_season()), int(nfl.get_current_week()))"
2025 22

$ .venv/bin/python3.14 -c "... week_status(2025, 22, schedule=_default_schedule_loader(2025, 22)) ..."
week 22 game count: 1 | statuses: {'final'}
week_status(2025, 22): finalized
```

**D2 — one leaked file descriptor per player read** (`src/dynasty_genius/capture/outcome_forward_capture_store.py:303`; same idiom at `:135`, `:270`). Python's `sqlite3` connection context manager (`with sqlite3.connect(...)`) ends the *transaction*; it never closes the *connection*. `_build_outcomes` calls `read_outcomes` once per gsis id (~1,800 in a full season) against launchd's 256-fd default → EMFILE exactly at the logged line.

**Reproduced:**
```
$ .venv/bin/python3.14 -c "<20 read_outcomes calls on a temp store, counting /dev/fd>"
fds before 20 reads: 5 | after: 25 | leaked: 20
```

**D3 — a dishonest artifact is one fix away.** If D2 alone were fixed, `run_scoring` would proceed past the finality gate, "score" season 2025 against `_default_prediction_loader` (unwired, returns `[]`, `scripts/run_realized_outcome_scoring.py:223-226`), and WRITE a `status: ok` scorecard (`:164-166`) — an artifact claiming a completed scoring run with zero predictions. The crash has been accidentally protecting the honesty substrate.

**Consequence today:** a scheduled job silently fails weekly (silence-is-not-success violation, 02 backup-law analogue); the moment anyone fixes the crash naively, a false `ok` scorecard ships.

## 2. Design

Four changes, ordered so no fix un-masks a deeper defect (robustness boundary defined up front, 02 §Falsification #8):

### 2.1 Predictions gate BEFORE any network loader (D1 + D3, one gate)

In `run_scoring`, load predictions FIRST (they are local/cheap) and no-op honestly when empty — before the schedule fetch, before `_build_outcomes`:

```python
predictions = prediction_loader(season, week)
if not predictions:
    return {"status": "noop", "noop_reason": "no_predictions_for_target", ...}
schedule = schedule_loader(season, week)   # only reached with real predictions
```

This single local gate covers today's off-season case (loader unwired → `[]`), the future outage case (wired loader, zero rows), and D3 (an `ok` scorecard now REQUIRES non-empty predictions by construction) — with zero calendar heuristics. **Rejected alternative (Gemini framing rule 1a, correction accepted):** "no-op when resolved season ≠ calendar year" breaks January in-season scoring (calendar 2027, live season 2026, playoffs finalizing weekly).

### 2.2 Scheduled-target freshness guard (Codex R1 — closes the stale-target hole)

The predictions gate alone leaves a hole once predictions are wired: the FIRST off-season scheduled run would find real frozen 2025 predictions, no prior same-target artifact, and score (2025, 22) months late. The guard is **schedule-date-anchored, not calendar-heuristic**: the schedule payload gains the week's game dates (nflreadpy `load_schedules` carries `gameday`; the default loader forwards it), and the **no-arg scheduled path** refuses a resolved target whose last game date is more than `SCHEDULED_TARGET_MAX_AGE_DAYS = 14` before today (clock injectable) → no-op `stale_target`. January playoffs (games days old) score; July (games in February) refuse. **Explicit `--season/--week` invocations BYPASS this guard** — a human-named target is an intentional backfill and stays legal; the guard binds only the unattended resolver path.

### 2.3 Already-scored gate — the MARKER is the target ledger (Codex R2)

The v1 idea of reading `(season, week)` from the existing scorecard is **unimplementable without contract drift**: `score()` emits only `as_of_week` (`realized_outcome_scorer.py:341`) and the route DTO forbids extra root fields (`realized_outcome_scorecard_models.py:91`). Instead the NEW status marker (§2.6) is the target ledger: it records `(season, week, status)`, and the scheduled path no-ops `already_scored` when the last marker shows `status=ok` for the same target. Named residual: the marker is gitignored and overwritten — if lost, one redundant (idempotent) re-score can occur, and the freshness guard usually refuses it anyway.

### 2.4 Injectable resolver seam (testability, not cleverness)

`_resolve_season_week(*, season_provider=None, week_provider=None)` — providers default to the nflreadpy calls. The resolver stays dumb; honesty lives in gates 2.1–2.3. The RED probes off-season / pre-season / January-playoffs / rollover deterministically through the seam (correction to Gemini F2: no system-date mocking).

### 2.5 Connection lifecycle (D2)

Wrap every per-call `sqlite3.connect` in this store with `contextlib.closing(...)` (sites `:135`, `:270`, `:303`):

```python
with closing(sqlite3.connect(self.db_path)) as conn, conn:
```

(`closing` guarantees close; the inner `conn` context keeps the existing transaction semantics.) The same idiom exists at 14 sites across 6 capture/what-changed modules — harmless where a process opens one connection and exits; the repo-wide sweep is a named follow-up (§3.5), NOT silently bundled here.

### 2.6 Terminal status marker (silence-is-not-success)

New gitignored marker `app/data/valuation_runtime/realized_outcome_scoring_status_latest.json`, written on EVERY terminal state inside a terminal-marker `try` wrapping the run (the proven backup-runner / market-divergence pattern):

```json
{"status": "ok|noop|failed", "noop_reason": "...", "failure_reason": "<named, e.g. outcome_build_failed:OperationalError>",
 "finished_at": "...", "season": 2025, "week": 22, "decision_supported": false}
```

Exit codes: `ok`/`noop` → 0; `failed` → 1. A marker-write failure itself exits non-zero with a stderr line (the one sanctioned stderr-only path). The marker records job execution state, NEVER model performance (Gemini overclaim guard): no accuracy numbers, no "model improved" copy. Plist unchanged — the default marker path is script-side.

**`--preflight` writes NO job marker (Codex R3).** Preflight is readiness-only/no-write law (existing contract `tests/contract/test_run_realized_outcome_scoring.py:97`) and stays so: it mutates neither scorecard nor marker. Otherwise future health wiring would read a readiness probe as an executed scheduled job.

## 3. Out of scope (named, not hidden)

1. **Wiring the real prediction/identity/util loaders** — go-live gated; validated at the David-gated first live finalized-week run (existing law).
2. **capture-health registration of the new marker** — a real slice of its own (config + the six-artifact pin test update, PR #135 pattern). Named follow-up ticket; until it lands, the marker is readable but not yet wired into `GET /api/system/capture-health` — stated plainly, not implied.
3. **`/api/realized-outcome` route contract change** (degrade on failed/stale marker — Gemini F4). Rides with follow-up 2; today's 200-inactive-on-absent-artifact contract (PR #104) is untouched by this spec.
4. **Scorer math** (`realized_outcome_scorer.score`) and all frozen-prediction/identity stores — untouched; the frozen-model constitution is not in play.
5. **Repo-wide `with sqlite3.connect` sweep** — 14 sites / 6 files share the non-closing idiom (evidence: grep 2026-07-11). Only this store's sites are in scope (they are the only per-row-loop callers). The sweep is a named hygiene follow-up so it cannot rot silently.
6. **Raising the launchd fd limit** — rejected: masks the leak, fixes nothing.

## 4. Falsification seeds — the RED matrix

Test path: `tests/contract/test_realized_outcome_offseason_honesty_red.py`. Test-construction law: drive `run_scoring`/`main` directly with injected loaders and monkeypatched marker/report paths (both gitignored — never assert live artifacts); fd probes count `/dev/fd` deltas directly (no constrained-fd mock — correction to Gemini F1).

| # | Seed (inputs/state) | Required behavior |
|---|---|---|
| F1 | 100 `read_outcomes` calls on a temp store | open-fd delta == 0 |
| F2 | repeated `ingest_week` calls (write path, `:270`; init `:135`) | open-fd delta == 0 |
| F3 | empty predictions + finalized week (loaders spied) | no-op `no_predictions_for_target`; schedule/stat/util loaders NEVER called; exit 0 |
| F4 | empty predictions | NO scorecard write/mutation; marker `noop` written |
| F5 | non-finalized week + real predictions (all loaders spied) | existing `week_not_finalized` no-op retained; marker written; no scorecard mutation; **ONLY the prediction loader may have been called — schedule finality check allowed, identity/stat/util loaders stay dark** (intentional amendment of the `test_run_realized_outcome_scoring.py:146` law — Codex R4) |
| F6 | stat_loader raises mid-build | marker `failed` with NAMED reason (`outcome_build_failed:<ExcName>`); exit 1; scorecard NOT mutated; marker write survives the exception (terminal-try ordering) |
| F7 | happy path (finalized RECENT week, real predictions, wired loaders as fixtures, injected clock) | scorecard written; marker `ok` + `finished_at` + (season, week); exit 0 |
| F8 | last MARKER shows `status=ok` for the same resolved (season, week) | no-op `already_scored` AFTER the predictions gate; no re-score; ordering: F3's reason wins when both apply (marker is the target ledger — Codex R2) |
| F9 | resolver seam: providers return stale completed-season (2025, 22) with no predictions | end-to-end scheduled path = marker `noop`, zero network-loader calls (the exact Tuesday scenario, hermetic) |
| F10 | marker path unwritable | exit != 0; stderr names the marker failure; no scorecard mutation |
| F11 | marker/scorecard content scan | `decision_supported=false`; no banned verdict/performance language in marker or noop outputs |
| F12 | `subprocess`/git guard | no git invocation on any path (existing law, retained) |
| F13 | **the stale-target hole (Codex R1)**: resolver seam returns (2025, 22), predictions NON-EMPTY, no prior marker, week finalized, last game date months before injected today | scheduled path no-ops `stale_target`; NO scoring; identity/stat/util loaders dark |
| F14 | same stale target invoked EXPLICITLY via `--season 2025 --week 22` | guard bypassed — intentional backfill scores normally (human-named target law) |
| F15 | `--preflight` (Codex R3) | readiness output only; NEITHER scorecard NOR job marker written (existing `:97` law retained against the new marker) |

Ordering discipline: a failure must not mask a different failure — F6 asserts the marker still records the ORIGINAL named reason if scorecard cleanup also fails; F3 → F8 → F13 gate precedence pinned (cheapest-and-most-honest reason first: no predictions, then already scored, then stale target).

## 5. Sequence (cockpit-TDD)

1. Cockpit CLEAR on this spec (Codex technical; Gemini advisory — framing already integrated with accepted corrections).
2. **David authorizes** the RED.
3. Codex authors the RED (F1–F15), demonstrably red on `main`.
4. Claude implements GREEN; focused suite + full gate (`verify_sprint_closeout`) since a scheduled job + store surface is touched; self-probes the falsification matrix including the real `/dev/fd` counts.
5. Codex independent review → CLEAR (falsification re-run on the changed surface).
6. **Only then, David-authorized:** commit → push → PR → CI (the merge gate) → merge word. The LaunchAgent needs NO reinstall (plist unchanged, script by absolute path — the #137 precedent); the Tue 07-14 10:00 fire becomes the live proof, and its marker (not silence) reports the result.

**Deadline context:** next scheduled fire Tue 2026-07-14 10:00. If the cycle cannot land by then, the honest interim is the crash (loud in launchctl, no dishonest artifact) — do NOT rush a partial fix that closes D2 without D3's gate.

## 6. Risks

| Risk | Mitigation |
|---|---|
| `no_predictions_for_target` cannot distinguish "loader unwired" from "wired but outage-empty" | Named residual, stated in the marker docstring; distinguishing requires loader self-description — follow-up when loaders are wired (go-live gated) |
| The marker is written but nothing consumes it yet | Stated plainly in §3.2/3.3 — surfacing automation lands with the capture-health follow-up; the LAW (silence must surface) binds now, the wiring is the named ticket (02 backup-law precedent) |
| `closing()` change alters transaction semantics | The inner `with conn` block is preserved verbatim; RED F1/F2 + the full existing store suite guard behavior |
| fd probe flakiness across platforms | `/dev/fd` exists on macOS + Linux (CI); delta-based assertion (not absolute counts) |
| Fixing the crash re-enables a future dishonest path we haven't imagined | F3/F4/F8/F9/F13/F15 pin every currently known path; the ordering rule (predictions gate FIRST, before any network call) fails closed by construction |
| This spec's own reproduction goes stale (nflreadpy convention changes) | The probes are dated (2026-07-11) and the resolver seam makes the RED independent of live nflreadpy behavior |
