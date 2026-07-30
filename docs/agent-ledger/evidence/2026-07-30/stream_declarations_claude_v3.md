# Stream Declarations — the three live sources, declared against real code — v3

**Authored by Claude Code, 2026-07-30.** David's word: **"answer 1: do the enumeration."**
**v1 NOT CLEAR (7 findings) · v2 NOT CLEAR (5 findings). All 12 accepted, none challenged.**
v1 (`7bdd5653…82407e`) and v2 (`c951883c…1a840a`) remain byte-unmodified on disk as frozen priors.

**Declaration work only.** No repair, no implementation, no config/schema/job change.
**Layer:** primary **1–2**; the work is at those layers, so no dependency check applies.

**Observation-anchoring rule adopted in this version.** Every on-disk observation below carries an
**as-of timestamp**. v2 carried a present-tense "verified on disk" reading that was true when written
at 08:45 and false by the time it was reviewed — the 09:30 job had run. **An unanchored observation
in a frozen artifact is a defect, and it is the same class as the stale-self-status pattern already
closed this morning.** I adopted that habit at 08:45 and violated it in a freeze at 10:50.

---

## §0 — Disposition of the v2 review

*(Scope: the five v2 findings only. This is not a general regression control and must not be read as
proof that unlisted v2 content survived unchanged.)*

| # | Finding | Disposition | Where |
| --: | :-- | :-- | :-- |
| 1 | The rebuilt pipeline contract is defined but **still not exercised** — no `publication_decision` / failure rows, destinations aggregated, real writes omitted, two `change_gate` cells wrong | **ACCEPTED** — reproduced | §2 rebuilt as filled per-pipeline blocks |
| 2 | `failure_visibility_coverage` declared but **not populated** for any pipeline | **ACCEPTED** — reproduced | §2, every block |
| 3 | The Sleeper delivery set is **still false** — `POST /refresh` request-triggers streams 1, 8, 9 | **ACCEPTED** — reproduced | §3a |
| 4 | Realized-outcome cadence is **Tuesday, not Monday** | **ACCEPTED** — reproduced | §2d, §3d |
| 5 | The present-tense disk observation was **stale in the freeze** | **ACCEPTED** — reproduced | §4, and the anchoring rule above |

**Root cause of 1, 2 and 3 — one error, and it is the second time it has been found.**
v1 finding 2 was an incomplete consumer enumeration; v2 finding 3 is *the same class* — I patched the
one consumer the reviewer named (the roster auditor) instead of enumerating consumers *systematically*.
Likewise v4 blocking 3, v1 finding 3 and v2 finding 1 are all one error: **I keep defining a
declaration form and shipping it unfilled.**

**Method changed in v3, not merely promised:**
1. **Consumer graph built by repo-wide scan** — every module importing the adapter, then every caller
   of those modules **including `subprocess` invocations**, which is exactly what hid `POST /refresh`.
2. **The form is filled for every unit before it is declared.** If a field cannot be filled for all
   four pipelines, the field is wrong.

---

## §1 — Declared unit set (floors, with method)

| Unit class | Count | Method / bound |
| :-- | :-- | :-- |
| Sleeper streams | **exactly 11 adapter endpoints** | Complete enumeration of `app/data/sleeper.py:15-85`. Exact for adapter-reachable endpoints only. |
| Sleeper objects known-omitted | **≥ 2** | `transactions` (no adapter), trending players (`source_registry.py:282-285`; recorded uncalled in `tw29_census_codex_runtime_trace.md:112,140-141`). |
| FantasyCalc streams | **1** | `fc_forward_capture_driver.py:31`. |
| nflreadpy objects | **≥ 6** | 5 in feature refresh (`run_feature_refresh.py:61-65`) + `load_schedules` (`run_realized_outcome_scoring.py:342`). |
| **Live ingestion streams** | **≥ 18** | Sum. |
| Ingestion pipelines | **≥ 4** | §2a–§2d. |
| Downstream publication pipelines | **≥ 2** | PVO refresh · market-divergence refresh. |

Stream↔pipeline is **many-to-many**: `load_player_stats` feeds both feature refresh and
realized-outcome scoring (`run_realized_outcome_scoring.py:370`).

---

## §2 — The pipeline contract, FILLED for all four pipelines

**Field set:** `pipeline_id` · `trigger` · `input_stream_ids` · `destinations[]` (each with
`destination_identity`, `destination_key`, `write_disposition`) · `acceptance_record` ·
`change_gate` · `publication_decision` · `failure_visibility` · `failure_visibility_coverage` ·
`replay_boundary`.

### §2a — `league_capture`

- **trigger:** scheduled, 09:20 local daily.
- **inputs:** 9 Sleeper streams (§3a).
- **destinations[]:**
  1. `app/data/league_runtime/runs/<run_id>/` — key `run_id` (single path segment, traversal-rejected
     `league_capture.py:53-55`; existing dir → `run_id_conflict` `:177`) — **run-immutable**, holding
     **six** artifacts (`ARTIFACTS:21-29`).
  2. `ready_latest.json` — singleton — **replace-whole**, atomic `os.replace` `:231-237`.
  3. `capture_status_latest.json` — singleton — **replace-whole** `:67-84`.
- **acceptance_record:** the ready marker, written **last**, naming the run and every artifact digest.
- **change_gate:** none. Every run captures.
- **publication_decision:** servable **iff** the marker names the run **and every named artifact
  re-hashes to the marker digest**; otherwise the loader falls back to committed seeds and **never
  scans `runs/`** (`:5-7`).
- **failure_visibility:** `capture_status_latest.json`, with a named reason.
- **failure_visibility_coverage — INCOMPLETE, and this is the finding:**
  | Failure class | Reaches the status surface? |
  | :-- | :-- |
  | `CaptureError` from fetch/validate (`:188-194`, `except` at `:193`) | ✅ `failed:<reason>` |
  | **Any other exception from `fetch_league_state()`** — e.g. a network `RuntimeError` | ❌ **propagates; no marker written at all** |
  | Any exception in `derive_chain` (`:196-200`) | ✅ `failed:derive_chain_error` |
  | Incomplete derived set | ✅ `derive_chain_incomplete_set` `:202` |
- **replay_boundary:** derivation — no per-stream raw retained.

### §2b — `fc_forward_capture`

- **trigger:** scheduled, 09:00 local daily.
- **inputs:** `fantasycalc/values_current`.
- **destinations[]:**
  1. `fc_forward_capture_raw` — key `(snapshot_date, source, settings_hash, player_key)`
     (`store:45`) — **append-immutable** (`INSERT OR IGNORE` `:202`).
  2. `fc_forward_capture_joinable` — same key — **append-immutable** (`:208`).
  3. `app/data/capture/fc_forward_capture_latest_report.json` — singleton — **replace-whole**
     (`driver:126-128`).
- **acceptance_record:** row presence keyed as above, plus `payload_hash` (`driver:222`); content
  signature excludes `retrieved_at` (`store:63-65`).
- **change_gate: NONE — corrected.** v2 named the immutable-conflict check as a change gate; it is
  **an abort**: a conflicting entry raises and the driver returns `abort(str(exc))`
  (`driver:205-207`). A same-content re-run is absorbed by `INSERT OR IGNORE`, which is idempotency,
  not a gate.
- **publication_decision:** none — the store is the destination; no downstream publish in this run.
- **failure_visibility:** the report artifact, always persisted on the abort path.
- **failure_visibility_coverage — COMPLETE, and the best in the estate:**
  `fatal_http_<code>` (non-transient) · `retry_exhausted_http_<code>` · `retry_exhausted_timeout`
  (both after bounded exponential backoff + jitter, `driver:176-191`) · normalize-rejection reason ·
  `malformed_payload_row` (`:195-200`) · store conflict / validation (`:203-207`). **Every class
  returns through `abort()` and persists the report.**
- **replay_boundary:** normalization.

### §2c — `feature_refresh`

- **trigger:** scheduled, 09:15 local daily.
- **inputs:** 5 nflreadpy objects.
- **destinations[]:**
  1. `engine_b_features_candidate.csv` — **replace-whole** (`feature_refresh_runner.py:83,118`).
  2. `feature_refresh_latest_report.json` — **replace-whole** (`:82,123,147`).
  3. the runtime CSV — **replace-whole**, atomic temp→replace (`feature_publish.py:103,146-147`).
  4. the ready marker — **replace-whole** (`:104,148-156`).
- **acceptance_record:** **the ready marker carrying `runtime_sha256` + the validation payload**,
  written after the atomic replace (`feature_publish.py:141-156`), with restore-on-failure of both
  prior runtime and prior ready bytes (`:157-160`).
- **change_gate:** **the collective source hash** — `feature_refresh_runner.py:101` returns a no-op
  when the hash is unchanged and the last status was not `blocked`.
- **publication_decision:** validation gate — non-empty candidate, all four positions present in the
  inference season (`run_feature_refresh.py:43-44,243-244`); on failure the report carries
  `blocked_reason` and the prior runtime stands (`feature_publish.py:135-139`).
- **failure_visibility:** the report artifact + exit code (`run_feature_refresh.py:257-262`).
- **failure_visibility_coverage — INCOMPLETE:**
  | Failure class | Reaches the report? |
  | :-- | :-- |
  | Validation failure | ✅ `blocked_reason`, prior runtime preserved |
  | Publish/write failure | ✅ restore + report |
  | **Upstream source unavailable (`ConnectionError`)** | ❌ **prints, `return 1` at `:222-224`; no report written — the stale prior report remains the newest artifact** |
- **replay_boundary:** derivation — no repo-local raw.

### §2d — `realized_outcome_scoring`

- **trigger:** scheduled, **Tuesday 10:00 local** — `StartCalendarInterval Weekday = 2`, and
  `launchd.plist(5)` states **0 and 7 are Sunday**, so 2 is Tuesday. **v2 said Monday twice; wrong.**
  Corroborated by the marker's own `finished_at 2026-07-28T14:00:05Z`, a **Tuesday**.
- **inputs:** `nflreadpy/schedules` (`:342`) + `nflreadpy/player_stats` (`:370`).
- **destinations[]:** the scorecard report — **replace-whole**, temp→marker→atomic publish
  (`:307-312`); the status marker — **replace-whole**.
- **acceptance_record:** the **ok marker**, written *before* the atomic publish, with the coupling
  rule that a publish failure **rewrites the marker to failed**, so **the marker can never vouch for
  a scorecard that was not published** (`:307-312`).
- **change_gate — corrected.** v2 named `noop_reason`, which is the *emitted result*. The real gates,
  in spec order (`:192-201`): (1) **predictions present** — empty → `no_predictions_for_target`;
  (2) **the marker as target ledger** — same `(season, week)` already `ok` → `already_scored`;
  (3) **week finality** → `week_not_finalized`; (4) **target freshness** → `stale_target`, with
  unparseable gamedays failing loud as `target_freshness_indeterminate`.
- **publication_decision:** publish only after the ok marker; otherwise the prior scorecard stands
  byte-unchanged.
- **failure_visibility:** the status marker — **every terminal state writes it**.
- **failure_visibility_coverage — COMPLETE, with one sanctioned exception:**
  loader failures → `predictions_load_failed:<Type>` / `schedule_load_failed:<Type>` (`:250,270`);
  all four gates → marker no-ops; **`MarkerWriteError` → stderr only, exit 1 (`:498-501`) — the one
  sanctioned stderr-only path, because the truth surface itself is unwritable.** That is a declared
  and defensible exception, not a silent failure.
- **replay_boundary:** derivation.

**What filling the form actually surfaced** — the thing a table of headings could not: **two of four
pipelines cannot report their most likely failure** (league capture's network fetch, feature
refresh's upstream outage), while the other two enumerate their failure classes completely. That
asymmetry is the declaration's most useful output so far, and it is **recorded, not opened.**

---

## §3 — Stream declarations

### 3a. Sleeper — 11 streams; `trigger` is a SET of three values

**Consumer graph, built by repo-wide scan (the method that was missing twice).** Five modules import
the adapter; each is then classified by what invokes *it*, **including subprocess paths**:

| Consumer module | Invoked by |
| :-- | :-- |
| `scripts/build_sleeper_universe_snapshot.py` | `run_league_snapshot_capture.py:40-42` → launchd 09:20 → **scheduled** |
| `app/services/roster_auditor.py` | `GET /api/roster/audit` (`app/api/routes/roster.py:14`) → **request** |
| `scripts/refresh_draft_state.py` | **`POST /refresh` via `subprocess` in `scripts/serve_rookie_board.py:70-88`** → **request**; also `__main__:139` → **manual** |
| `scripts/ingest_2026_draft.py` | `__main__:79` → **manual** |
| `scripts/calibrate_sf_qb_knob.py` | `__main__:423` → **manual** |

| # | `stream_id` | adapter | grain | **trigger set** |
| --: | :-- | :-- | :-- | :-- |
| 1 | `sleeper/league_drafts` | `:57` | draft × league | **scheduled · request · manual** (`refresh_draft_state.py:81`; `calibrate:151`) |
| 2 | `sleeper/league` | `:29` | league | scheduled · manual (`calibrate:149,198`) |
| 3 | `sleeper/rosters` | `:36` | roster × league | **scheduled · request** (`roster_auditor.py:436-439`) |
| 4 | `sleeper/users` | `:43` | user × league | scheduled |
| 5 | `sleeper/traded_picks` | `:50` | pick × league | scheduled |
| 6 | `sleeper/players_nfl` | `:78` | player | **scheduled · request · manual** (`roster_auditor.py:446`; `ingest_2026_draft.py:32`) |
| 7 | `sleeper/nfl_state` | `:85` | league-year singleton | scheduled |
| 8 | `sleeper/draft` | `:64` | draft | **scheduled · request · manual** (`refresh_draft_state.py:105-108`; `calibrate:152,193`) |
| 9 | `sleeper/draft_picks` | `:71` | pick × draft | **scheduled · request · manual** (`refresh_draft_state.py:105-108`; `calibrate:156,209`) |
| 10 | `sleeper/user` | `:15` | user | request only |
| 11 | `sleeper/leagues_for_user` | `:22` | league × user × season | request only |

**Corrected tally: 4 scheduled-only · 2 scheduled+request · 3 scheduled+request+manual · 2
request-only.** v2's "7 / 2 / 2" is retracted. **Five streams — not two — carry an unbounded
request-time call rate**, and the adapter declares **no retry, no backoff and no explicit timeout**
for any of them (`:8-12`) — a contrast worth naming, because the FantasyCalc driver *does* implement
bounded retry with backoff and jitter (`driver:176-191`).

**Persistence:** streams 1–9 retain no independent raw; only the composite snapshot is written. Per-
stream replay is impossible. Streams 10–11 persist nothing.

### 3b. FantasyCalc — 1 stream

Unchanged and twice independently reproduced: pinned settings query hashed into `SETTINGS_HASH`
(`driver:31-32`); PK `(snapshot_date, source, settings_hash, player_key)`; append-immutable;
three-state volatility enum `captured | source_omitted | structurally_unavailable` (`store:52-59`) —
the pattern the declaration should propagate. TW26Q correction (scaled one-QB feed, not observed
superflex trades) carried, unresolved.

### 3c. nflreadpy — ≥ 6 objects across two pipelines

`player_stats` (**both pipelines**) · `rosters` · `snap_counts` · `pbp` · `participation`
(**≥ 2019 only**, `:59`, a different window from its siblings inside one collective hash) ·
**`schedules`** (realized-outcome, `:342`). Offseason boundary fails closed after one ceiling
step-down (`:69-92`) — a good contract, declared only in a docstring.

### 3d. Realized-outcome scoring — the fourth pipeline

**Tuesday 10:00 weekly**, `dormant_ok`, `tier=auxiliary`, registered with `timestamp_field=finished_at`,
`status_field=status`, `success_status=[ok,noop]`. Marker as of **2026-07-30 ~11:05 ET**:
`status=noop`, `noop_reason=no_predictions_for_target`, `finished_at=2026-07-28T14:00:05Z`. It runs
and correctly reports having nothing to score.

---

## §4 — Freshness detection (observations anchored)

**Provenance: Tower established the file-newer-than-its-data condition by opening an artifact;
Gemini's 2026-07-29 telemetry is the earliest record of the shape in the repo. This section is
corroboration and mechanism.**

1. **`GET /api/system/capture-health`** reads **SQLite row dates**, never mtime
   (`system_capture_health_models.py:614-658`) — structurally immune. **Coverage: 2 registered
   stores, of which `model_forward_capture` is produced downstream (`run_pvo_refresh.py:1-15`), so
   exactly ONE enumerated ingestion stream (`fc_forward_capture`) of ≥18.**
2. **The report-freshness evaluator** (`system_health_models.py:439-480`) prefers the embedded
   timestamp, falls back to **mtime** with the disclosure `timestamp_source:mtime_fallback` (`:464`),
   and treats a future timestamp as an anomaly (`:480`).

**Of the 8 registered artifacts, `pvo_refresh` alone declares neither `timestamp_field` nor
`status_field`** — twice independently confirmed by the reviewer.

**Observation, anchored — and it moved between v2 and v3, which is itself the point:**

| As of | mtime | `capture_report.capture_date` | registry `timestamp_field` |
| :-- | :-- | :-- | :-- |
| 2026-07-30 **08:45 ET** (v1/v2 reading) | `2026-07-29T13:30:26Z` | `2026-07-29` | `null` |
| 2026-07-30 **~11:05 ET** (v3 reading, after the 09:30 job) | `2026-07-30 09:37 local` | `2026-07-30` | `null` |

**The value changed under a frozen document in about two hours.** That is exactly why an
unanchored on-disk claim is a defect — and it is also live evidence for the mechanism: the artifact's
mtime advances daily while **nothing in the registry reads its embedded vintage or its `status`
field.** A touch, copy, restore or partial rewrite would advance the same basis with no data change
at all, and the artifact's own `"status"` could not contradict it.

**What the declaration requires:** `observation_timestamp_field` (finest granularity available — a
date cannot answer a 26-hour question) · `producer_status_field` where one exists ·
`freshness_basis` materialized as `embedded | mtime_fallback` · and the consumer rule that **file
mtime is never a freshness basis without an emitted disclosure, and an mtime-vs-embedded divergence
is reportable rather than silently resolved toward the newer value.**

**Detectable and declarable — not fixed.** No change to `report_freshness.json` is proposed here.

---

## §5 — Contract v4 findings (arithmetic unchanged from v2)

**Addressed: blocking 3** (§2, now actually filled for four pipelines) and **blocking 4** (§3a, one
row per endpoint with a systematically derived trigger set).
**Open: blocking 1, blocking 2, blocking 5, and the material run-record finding. TWO of six
addressed, FOUR open.** No revision to contract v4 has been authored.

## §6 — Registry drift: established vs not (unchanged from v2)

- **`nfl_data_py` vs `nflreadpy` — NOT established as a defect.** The key was **intentionally
  retained per David's own scope confirmation** (`docs/agent-ledger/2026-05-11.md:315-323`), and the
  entry is not read by the feature-refresh runner. A naming mismatch exists; a defect does not follow.
- **`sleeper` `freshness_hours=1` — CONDITIONAL** on David's open semantics question: a contradiction
  if the field means ingest interval, no contradiction if it means cache TTL.
- **Established, and the substantive point:** the registry's grain is **source**, so 11 Sleeper
  endpoints and ≥6 nflreadpy objects are **inexpressible in it.**

## §7 — Declared unknowns

1. Per-endpoint Sleeper timeout/retry semantics — undeclared; sharper now that **five** streams carry
   request-time call rates.
2. `freshness_hours` semantics — David's open question.
3. Late-data / backfill policy — no stream declares one.
4. Whether the two request-only streams should carry a cadence at all.
5. **Whether ≥18 / ≥4 are the true totals.** The method establishes floors; a consumer outside the
   adapter file and the scheduled runners would not have been found by it — which is precisely how
   `POST /refresh` was missed once already.

## §8 — The one question needed at landing, not at start

**Where does this declaration live** — an extension of `SOURCE_REGISTRY`, which §6 shows cannot
express the unit, or a new declaration artifact? Unanswered; it did not block the work.
