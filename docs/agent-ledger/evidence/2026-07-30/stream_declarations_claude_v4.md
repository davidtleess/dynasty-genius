# Stream Declarations — the three live sources, declared against real code — v4

**Claude Code, 2026-07-30.** David's word: *"answer 1: do the enumeration."*
**v1 NOT CLEAR (7) · v2 NOT CLEAR (5) · v3 NOT CLEAR (6). All 18 findings accepted, none challenged.**
Priors v1 `7bdd5653…`, v2 `c951883c…`, v3 `7297f09b…` remain byte-unmodified on disk.

**Declaration work only.** No repair, no producer touched, no config change.
**Layer:** 1–2. **Observation-anchoring rule in force** (§ every on-disk reading carries an as-of).

---

## §0 — THE STRUCTURAL CHANGE IN THIS VERSION: no completeness claims

**Three consecutive rounds have falsified a completeness claim of mine, each time one layer deeper:**
v1 claimed "exactly 17"; v2 claimed an exclusive delivery split; **v3 claimed a *systematic* consumer
graph and was falsified by a subprocess caller that appeared in my own earlier scan output.** The
pattern is not "I missed three things." It is that **my assertions of exhaustiveness are not
reliable, so this document stops making them.**

**What replaces them:**

1. **Every enumeration states its method and what the method cannot see.** No count is presented as
   complete. Counts are floors; the method is the claim.
2. **A reviewer finding is not a patch to a claim — it is a row in the enumeration.** The consumer
   graph below is explicitly "enumerated to date, known-incomplete, growing."
3. **No absolute guarantee is repeated from a docstring without a probe.** v3 asserted the
   realized-outcome marker "can never vouch for an unpublished scorecard" because the source
   docstring says so. The reviewer broke it in the termination window (§0 finding 5). **A comment
   describing an invariant is not evidence the invariant holds.**

### Disposition of the v3 review

*(Scope: the six v3 findings only. Not a general regression control.)*

| # | Finding | Disposition |
| --: | :-- | :-- |
| 1 | Consumer graph still incomplete — `refresh_league_intelligence.py` subprocess-invokes the builder; the builder has its own `__main__` | **ACCEPTED** — reproduced (`refresh_league_intelligence.py:23-24,43-68`; `build_sleeper_universe_snapshot.py:96-105`) |
| 2 | Pipeline forms still not filled to their own contract — missing `destination_key`s, missing manual triggers, understated publication gate and failure matrices | **ACCEPTED** — reproduced |
| 3 | FantasyCalc coverage is not COMPLETE — only three httpx classes caught | **ACCEPTED** — reproduced (`fc_forward_capture_driver.py:176-191`) |
| 4 | Realized coverage is not COMPLETE — `_resolve_season_week()` runs outside the only catch | **ACCEPTED** — reproduced (`run_realized_outcome_scoring.py:476-484`) |
| 5 | The realized acceptance claim is false — ok marker is written *before* the atomic publish | **ACCEPTED** — reproduced (`:324-330`) |
| 6 | The anchoring rule is violated inside the artifact that declares it | **ACCEPTED** — my own text |

---

## §1 — Units (floors; method stated)

| Unit class | Count | Method — and its blind spot |
| :-- | :-- | :-- |
| Sleeper streams | 11 adapter endpoints | Enumeration of `app/data/sleeper.py:15-85`. **Blind to:** objects Sleeper offers that were never adapted. |
| Sleeper objects known-omitted | ≥ 2 | `transactions` (no adapter); trending players (`source_registry.py:282-285`). **Blind to:** the rest of the API surface. |
| FantasyCalc streams | 1 | `fc_forward_capture_driver.py:31`. |
| nflreadpy objects | ≥ 6 | 5 in feature refresh + `load_schedules` (`run_realized_outcome_scoring.py:342`). **Blind to:** consumers outside the traced runners. |
| Live ingestion streams | ≥ 18 | Sum of floors. |
| Ingestion pipelines | ≥ 4 | §2. **Blind to:** any producer not reached from the LaunchAgent set. |

## §2 — Pipeline forms, filled — with coverage stated honestly

**Field set:** `pipeline_id` · `trigger[]` · `input_stream_ids` · `destinations[]` (each with
`destination_identity`, `destination_key`, `write_disposition`) · `acceptance_record` · `change_gate`
· `publication_decision` · `failure_visibility` + `failure_visibility_coverage` · `replay_boundary`.

### §2a `league_capture`
- **trigger[]:** scheduled 09:20 · **manual** (`run_league_snapshot_capture.py:92-121`, whose own
  docstring states hand-running *is* the supervised real run) · **manual via orchestrator**
  (`refresh_league_intelligence.py` PHASE_STEPS → subprocess).
- **destinations[]:** (1) `runs/<run_id>/` — key **`run_id`** — run-immutable, **six** artifacts;
  (2) `ready_latest.json` — key **fixed singleton path** — replace-whole, `os.replace` `:231-237`;
  (3) `capture_status_latest.json` — key **fixed singleton path** — replace-whole `:67-84`.
- **acceptance_record:** ready marker, written last, naming every artifact digest.
- **change_gate:** none.
- **publication_decision:** servable iff the marker names the run and every artifact re-hashes to its
  digest; else committed seeds, never a `runs/` scan (`:5-7`).
- **failure_visibility_coverage — PARTIAL (and better than v3 said in two places):**
  | Class | Marker written? |
  | :-- | :-- |
  | `CaptureError` from fetch/validate (`:193`) | ✅ |
  | **Any other exception from `fetch_league_state()`** | ❌ **propagates, no marker** |
  | derive-chain exception (`:196-200`) | ✅ `failed:derive_chain_error` |
  | incomplete derived set (`:202`) | ✅ |
  | **artifact write failure (`:214-221`)** | ✅ `failed:artifact_write_error` *(v3 omitted this)* |
  | **publish rename / torn publish (`:238-241`)** | ✅ `failed:publish_rename_error`, prior marker keeps serving *(v3 omitted this)* |

### §2b `fc_forward_capture`
- **trigger[]:** scheduled 09:00 · manual CLI (`--db-path` required).
- **destinations[]:** (1) `fc_forward_capture_raw` — key `(snapshot_date, source, settings_hash,
  player_key)` — append-immutable; (2) `fc_forward_capture_joinable` — same key — append-immutable;
  (3) `fc_forward_capture_latest_report.json` — key **fixed singleton path** — replace-whole.
- **acceptance_record:** row presence + `payload_hash`; content signature excludes `retrieved_at`.
- **change_gate:** none — the immutable-conflict check **aborts**; `INSERT OR IGNORE` is idempotency.
- **failure_visibility_coverage — PARTIAL, corrected from v3's "COMPLETE":**
  covered → `fatal_http_<code>` · `retry_exhausted_http_<code>` · `retry_exhausted_timeout` ·
  normalize rejection · `malformed_payload_row` · store conflict/validation.
  **NOT covered → any non-httpx exception from `fetch_json` (only `HTTPStatusError`,
  `TimeoutException`, `TransportError` are caught, `:176-191`) — it propagates and NO report is
  written. Report-write and SQLite-level failures are likewise unlisted.**

### §2c `feature_refresh`
- **trigger[]:** scheduled 09:15 · manual CLI · manual via orchestrator.
- **destinations[]:** (1) `engine_b_features_candidate.csv` — key **fixed path** — replace-whole;
  (2) `feature_refresh_latest_report.json` — key **fixed path** — replace-whole; (3) runtime CSV —
  key **fixed path** — replace-whole, atomic temp→replace; (4) ready marker — key **fixed path** —
  replace-whole.
- **acceptance_record:** ready marker with `runtime_sha256` + validation payload, after atomic
  replace, with restore-on-failure of prior runtime **and** prior ready bytes.
- **change_gate:** collective source hash (`feature_refresh_runner.py:101`).
- **publication_decision — v3 understated this badly.** Not merely "non-empty + four positions":
  `feature_validation.py:86-244` enforces **prohibited market/leakage columns, temporal leakage,
  required-schema columns, critical-feature columns, dtype rules, blank player ids, inference-season
  presence** and more, each appending a named failure. The row/position floors are two conditions
  among many.
- **failure_visibility_coverage — PARTIAL:** validation failure ✅ (`blocked_reason`, prior runtime
  preserved) · publish/write failure ✅ (restore + report) · **lock refusal (`run_feature_refresh.py:190-196`)
  — refuses fast before any load; report behaviour unverified by me** · **pre-publish assembly/read
  failures (`feature_refresh_runner.py:113-118`) — unverified by me** · **upstream `ConnectionError`
  ❌ prints, `return 1` at `:222-224`, no report written.**

### §2d `realized_outcome_scoring`
- **trigger[]:** scheduled **Tuesday 10:00** (`Weekday = 2`; launchd counts 0 and 7 as Sunday) ·
  manual CLI with explicit `--season/--week` (an intentional backfill path, `:476-479`).
- **destinations[]:** (1) scorecard report — key **fixed path** (`report_path`) — replace-whole via
  temp→`os.replace`; (2) status marker — key **fixed path** — replace-whole.
- **acceptance_record — CORRECTED, and the correction is a real integrity gap.** v3 said the ok
  marker "can never vouch for a scorecard that was not published," repeating the source docstring.
  **The code writes the ok marker at `:324-325` and publishes the scorecard at `:329-330`.** The
  `OSError` handler restores truth for ordinary write failures — **but an interruption between those
  two statements (`KeyboardInterrupt`, `SIGTERM`, power loss) leaves `status=ok` with no scorecard on
  disk.** The reviewer proved it with a termination-window probe. **The guarantee holds for
  `OSError`-class failures and fails in the termination window.**
- **change_gate:** four ordered gates (`:192-201`) — predictions present · marker-as-target-ledger
  (`already_scored`) · week finality · target freshness (`stale_target`,
  `target_freshness_indeterminate`). `noop_reason` is the emitted result, not the gate.
- **failure_visibility_coverage — PARTIAL, corrected from v3's "COMPLETE":** loader failures ✅
  (`predictions_load_failed:<Type>`, `schedule_load_failed:<Type>`) · four gates ✅ · `MarkerWriteError`
  → stderr-only, exit 1 (declared, defensible) · **`_resolve_season_week()` runs at `:476-482`,
  OUTSIDE the only `try` (`:484`) — an exception there propagates with NEITHER marker NOR report.**

---

## §3 — THE SUBSTANTIVE OUTPUT: five silent-failure paths across four pipelines

Filling the form — rather than declaring it — surfaced this, and it is the thread's real product:

| # | Pipeline | Failure that leaves NO durable record | Evidence |
| --: | :-- | :-- | :-- |
| 1 | league capture | any non-`CaptureError` from the Sleeper fetch | `league_capture.py:188-194` |
| 2 | feature refresh | upstream `ConnectionError` | `run_feature_refresh.py:222-224` |
| 3 | FC capture | any non-httpx exception from `fetch_json` | `fc_forward_capture_driver.py:176-191` |
| 4 | realized outcome | any exception in `_resolve_season_week()` | `run_realized_outcome_scoring.py:476-484` |
| 5 | realized outcome | **termination between ok-marker and scorecard publish → marker says `ok`, no scorecard** | `:324-330` |

**Every one is the same shape as the defect the backup law addresses: the status surface can be
silent or wrong precisely when the run failed.** #5 is the sharpest — a marker asserting success for
an artifact that does not exist. **All five are RECORDED, NOT OPENED.** No repair is authorised and
none is proposed here.

## §4 — Consumer graph (enumerated to date; known-incomplete)

| Consumer module | Invoked by |
| :-- | :-- |
| `build_sleeper_universe_snapshot.py` | `run_league_snapshot_capture.py:40-42` → launchd → **scheduled**; **its own `__main__:96-105`** → manual; **`refresh_league_intelligence.py:23-24,43-68` subprocess** → manual-via-orchestrator |
| `roster_auditor.py` | `GET /api/roster/audit` → **request** |
| `refresh_draft_state.py` | `POST /refresh` subprocess (`serve_rookie_board.py:70-88`) → **request**; `__main__:139` → manual |
| `ingest_2026_draft.py` | `__main__:79` → manual |
| `calibrate_sf_qb_knob.py` | `__main__:423` → manual |

**Method:** adapter importers, then callers of those modules, then subprocess call sites, then each
called module's own entry point. **Blind spot, stated rather than claimed away:** any invocation
path not reachable by that traversal — a shell alias, a notebook, a future orchestrator, a
`Makefile`. **This table grows; it is not asserted complete.**

**Trigger sets, corrected:**

| Streams | Trigger set |
| :-- | :-- |
| 2, 4, 5, 7 (`league`, `users`, `traded_picks`, `nfl_state`) | scheduled · manual |
| 1, 8, 9 (`league_drafts`, `draft`, `draft_picks`) | scheduled · request · manual |
| 3, 6 (`rosters`, `players_nfl`) | scheduled · request · manual |
| 10, 11 (`user`, `leagues_for_user`) | request only |

**Five request-bearing streams** (1, 3, 6, 8, 9) — unchanged and independently confirmed — against an
adapter with no retry, no backoff and no explicit timeout (`sleeper.py:8-12`), while the FantasyCalc
driver implements bounded retry with backoff and jitter.

## §5 — Freshness (observations anchored)

**Provenance: the file-newer-than-its-data condition is TOWER'S**, established by opening the
artifact; Gemini's 2026-07-29 telemetry is its earliest record in the repo.

- Capture-health reads SQLite row dates, never mtime — structurally immune; **covers 1 enumerated
  ingestion stream of ≥18.**
- The report-freshness evaluator prefers embedded timestamps, falls back to mtime with the disclosure
  `timestamp_source:mtime_fallback`, and treats future timestamps as anomalies.
- **`pvo_refresh` alone declares neither `timestamp_field` nor `status_field`.** Anchored readings:
  **as of 2026-07-30 08:45 ET** — mtime `2026-07-29T13:30:26Z`, `capture_date 2026-07-29`;
  **as of 2026-07-30 ~11:05 ET** — mtime `2026-07-30 09:37` local, `capture_date 2026-07-30`.
  The value moved under a frozen document, which is the mechanism demonstrating itself.

Declaration requirements unchanged from v3: `observation_timestamp_field` · `producer_status_field` ·
`freshness_basis` materialized · and mtime is never a freshness basis without an emitted disclosure.
**Superseded in part by TW30-WORD-K:** David has since ruled freshness is judged by **content**; the
content-basis definition lives in `content_basis_freshness_claude_v1.md` and governs.

## §6 — Priors, anchored (v3 finding 6)

`stream_declarations_claude_v1.md` `7bdd5653…82407e` and `_v2.md` `c951883c…1a840a` — **re-hashed as
of 2026-07-30 ~11:15 ET** and byte-identical to their freeze values at that moment. v3 stated this
without an as-of, inside the document that declared the anchoring rule.

## §7 — Contract v4 findings: TWO of six addressed, FOUR open. No amendment authored.

## §8 — Declared unknowns

1. Sleeper per-endpoint timeout/retry semantics — undeclared.
2. `freshness_hours` semantics — **demoted** by the content-basis ruling; still unanswered as history.
3. Late-data / backfill policy — no stream declares one.
4. **Whether §2c's lock-refusal and pre-publish assembly paths write a report — named by the
   reviewer, NOT verified by me**, and carried as unknown rather than assumed.
5. Whether ≥18 / ≥4 are the true totals. **The method finds floors. Three rounds have shown the
   floors rise when someone looks with a different traversal.**

## §9 — The landing question, unchanged

**Where does this declaration live** — `SOURCE_REGISTRY` cannot express the unit, so: extend it, or a
new artifact? Needed at landing, not to start.
