# Stream Declarations — the three live sources, declared against real code — v2

**Authored by Claude Code, 2026-07-30.** David's word: **"answer 1: do the enumeration."**
**v1 NOT CLEAR — 7 findings (3 blocking, 3 material, 1 record). All seven ACCEPTED, none challenged.**
v1 remains on disk unmodified as the frozen prior (`stream_declarations_claude_v1.md`,
SHA-256 `7bdd5653…82407e`).

**Declaration work only.** No repair, no implementation, no dependency, no schema/job/config change.
**Layer:** primary **1–2**; no layers 1–2 dependency check applies, because the work is at those layers.

---

## §0 — Disposition of the v1 review

**Scope of this table, stated so it cannot rot into a false control:** it covers **the seven findings
of the v1 review and nothing else.** It is not a general regression ledger and must not be read as
proof that unlisted v1 content survived unchanged — that overreach is what turned contract v4's §A
into a defect of its own.

| # | Finding | Disposition | Where |
| --: | :-- | :-- | :-- |
| 1 | Census not exhaustive — realized-outcome is a 4th pipeline over `load_schedules`; trending is a second omitted Sleeper object | **ACCEPTED** — reproduced | §1, §3c, §3d |
| 2 | Sleeper delivery split is not exclusive — rows 3 and 6 are scheduled **and** on-request | **ACCEPTED** — reproduced | §3a |
| 3 | Pipeline contract not exercisable as filled — single `write_disposition`, 4-vs-6 artifacts, wrong acceptance record | **ACCEPTED** — reproduced | §2 |
| 4 | Two `failure_visibility` cells claim surfaces ordinary upstream failures never write | **ACCEPTED** — reproduced by reading both exception boundaries | §2, §2a |
| 5 | Capture-health denominator wrong — 1 enumerated ingestion stream, not 2 | **ACCEPTED** — reproduced | §4 |
| 6 | §6 called two registry mismatches "confirmed" ahead of the evidence | **ACCEPTED** — one is a David-scoped intentional alias; the other contradicts my own §7 | §6 |
| 7 | §5 arithmetic false — 2 of 6 addressed, not 3 of 3 | **ACCEPTED** — my own table proves it | §5 |

**Root cause of 1, 2 and 5, named rather than patched three times:** I **stated exact totals from a
method that can only establish a lower bound.** Enumerating `app/data/sleeper.py` proves what that
file contains; it proves nothing about objects reached from elsewhere or never adapted. Worse, for
finding 2 **my own call-site trace already showed `get_rosters` and `get_all_players` inside the
roster auditor, and I wrote an exclusive split anyway** — the evidence was in hand and the claim did
not follow it. **Every count in v2 is therefore declared as a floor with its method attached.**

---

## §1 — The declared unit set (floors, with method)

| Unit class | Count | Method — and what it cannot establish |
| :-- | :-- | :-- |
| Sleeper streams | **exactly 11 adapter endpoints** | Complete enumeration of `app/data/sleeper.py:15-85`. **Exact for adapter-reachable endpoints; says nothing about objects the API offers that we never adapted.** |
| Sleeper objects known-omitted | **≥ 2** | `transactions` (no adapter) + trending players, named in `source_registry.py:282-285` notes and recorded as uncalled in `tw29_census_codex_runtime_trace.md:112,140-141`. **A floor, not a census of everything Sleeper offers.** |
| FantasyCalc streams | **1** | Single pinned endpoint, `fc_forward_capture_driver.py:31`. |
| nflreadpy objects | **≥ 6** | 5 in feature refresh (`run_feature_refresh.py:61-65`) + `load_schedules` in realized-outcome scoring (`run_realized_outcome_scoring.py:342`). **Found by tracing scheduled runners; another consumer could add more.** |
| **Live ingestion streams** | **≥ 18** | Sum of the above. **v1 said "exactly 17". Retracted.** |
| Ingestion pipelines | **≥ 4** | league capture · FC forward capture · feature refresh · **realized-outcome scoring** (weekly, `dormant_ok`). |
| Downstream publication pipelines | **≥ 2** | PVO refresh · market-divergence refresh. |

**Stream↔pipeline is many-to-many, and v1's model could not express it.** `load_player_stats` is
consumed by **both** feature refresh and realized-outcome scoring
(`run_realized_outcome_scoring.py:370`). A stream is not owned by the pipeline that happens to be
listed beside it.

---

## §2 — What a pipeline must declare (v2 — Codex finding 3 rebuilt, not patched)

v1's contract failed on contact with a real pipeline three separate ways. The corrected field set:

`pipeline_id` · `input_stream_ids` · **`destinations[]`** — and for **each** destination:
`destination_identity`, `destination_key`, `write_disposition`
(`append-immutable | replace-whole | merge-by-key | run-immutable`) · `acceptance_record` (what makes
the write ACCEPTED, distinct from what detects change) · `change_gate` (what may cause a run to
no-op) · `publication_decision` · **`failure_visibility` + `failure_visibility_coverage`** (§2a) ·
`replay_boundary`.

**Three corrections carried by that shape:**

1. **`destinations[]` is a list, because a composite pipeline writes several destinations under
   different semantics.** League capture creates a **conflict-refusing immutable run directory**
   (`league_capture.py:175-177`) *and separately replaces* the ready/status singletons
   (`:67-84,231-242`). v1's single "replace-whole, run-immutable" was not a declared value and hid
   the dual disposition.
2. **`acceptance_record` ≠ `change_gate`.** For feature refresh, the collective source hash is a
   **no-op gate** — `feature_refresh_runner.py:101` returns early when the hash is unchanged and the
   last status was not `blocked`. **The acceptance record is the ready marker carrying
   `runtime_sha256` plus the validation payload, written after the atomic replace**
   (`features/feature_publish.py:141-156`). v1 named the change detector as the acceptance record.
3. **The league-capture artifact set is SIX, not four** — `ARTIFACTS` at `league_capture.py:21-29`
   (`snapshot`, `coverage`, `team_posture`, `team_value_matrix`, `roster_cut_report`,
   `provenance`). v1's "4 named artifacts" conflated it with `TRACKED_SEED_PATHS:38-43`, a different
   tuple serving a different rule.

| Field | league capture | FC forward capture | feature refresh | realized-outcome scoring |
| :-- | :-- | :-- | :-- | :-- |
| Schedule | 09:20 daily | 09:00 daily | 09:15 daily | **Mon 10:00 weekly**, `dormant_ok` |
| Inputs | 9 Sleeper endpoints | FantasyCalc `values/current` | 5 nflreadpy objects | `load_schedules` + `load_player_stats` |
| Destinations | run dir **run-immutable** + marker/status **replace-whole** | 2 tables **append-immutable** | runtime CSV **replace-whole** | status marker **replace-whole** |
| Destination key | `run_id`, traversal-rejected `:53-55` | `(snapshot_date, source, settings_hash, player_key)` `:45` | none (whole artifact) | none (singleton) |
| Acceptance record | marker written last, `os.replace` `:231-237`; servable iff every artifact re-hashes to the marker digest `:5-7` | row presence + `payload_hash` | **ready marker: `runtime_sha256` + validation** | `finished_at` + `status` in the marker |
| Change gate | none | immutable-conflict check `:177-190` | **source hash** `feature_refresh_runner.py:101` | `noop_reason` (current marker: `no_predictions_for_target`) |
| Replay boundary | derivation | normalization | derivation | derivation |

### §2a — `failure_visibility_coverage` (Codex finding 4)

**A named status surface is not the same as a surface that ordinary failures reach.** Both v1 cells
overclaimed, and the exception boundaries show exactly where:

- **League capture:** the fetch/validate block catches **`CaptureError` only**
  (`league_capture.py:188-194`, the `except` at `:193`). A `RuntimeError` from
  `fetch_league_state()` — the ordinary shape of a network failure — **propagates without writing
  `capture_status_latest.json` at all.** The derive stage, by contrast, catches broad `Exception` and
  *does* write `failed:derive_chain_error` (`:196-200`). **Fetch failures are invisible on the status surface;
  derive failures are visible.**
- **Feature refresh:** an upstream `ConnectionError` prints and `return 1` **before any report is
  written** (`run_feature_refresh.py:222-224`). The stale prior report remains the newest artifact
  on disk.

**So the declaration requires `failure_visibility_coverage` — which failure CLASSES reach the named
surface — because "there is a status file" is exactly the assurance that fails silently.** This is
the same shape as the marker-vs-reality gap the backup law addresses, arrived at from the other end.
**Named, not opened:** no fix to either boundary is proposed here.

---

## §3 — Stream declarations

### 3a. Sleeper — 11 streams, delivery is NOT an exclusive split

`BASE_URL = https://api.sleeper.app/v1` (`app/data/sleeper.py:5`). No auth. All 11 go through `_get`
(`:8-12`) with **no retry, no backoff, no explicit timeout** — the httpx default applies, declared
nowhere.

| # | `stream_id` | adapter | grain | delivery | evidence |
| --: | :-- | :-- | :-- | :-- | :-- |
| 1 | `sleeper/league_drafts` | `:57` | draft × league | scheduled | `build_sleeper_universe_snapshot.py:54` |
| 2 | `sleeper/league` | `:29` | league | scheduled | `:65` |
| 3 | `sleeper/rosters` | `:36` | roster × league | **scheduled + on-request** | `:66` **and** `roster_auditor.py:436-439` |
| 4 | `sleeper/users` | `:43` | user × league | scheduled | `:67` |
| 5 | `sleeper/traded_picks` | `:50` | pick × league | scheduled | `:68` |
| 6 | `sleeper/players_nfl` | `:78` | player | **scheduled + on-request** | `:69` **and** `roster_auditor.py:446` |
| 7 | `sleeper/nfl_state` | `:85` | league-year singleton | scheduled | `:70` |
| 8 | `sleeper/draft` | `:64` | draft | scheduled | `:76` |
| 9 | `sleeper/draft_picks` | `:71` | pick × draft | scheduled | `:77` |
| 10 | `sleeper/user` | `:15` | user | on-request only | `roster_auditor.py:415` |
| 11 | `sleeper/leagues_for_user` | `:22` | league × user × season | on-request only | `roster_auditor.py:424` |

**`delivery` is therefore a SET, not an enum value** — 7 scheduled-only, 2 scheduled + on-request, 2
on-request-only. v1's "9 / 2" split is retracted. The on-request path is
`GET /api/roster/audit` (`app/api/routes/roster.py:14`), which means **two streams have both a
cadence and an unbounded request-time call rate**, and no declared timeout on either.

**Persistence:** streams 1–9 have **no independent raw persistence** — only the composite snapshot is
written (`league_capture.py:21-29`), so per-stream replay is impossible. Streams 10–11 persist
nothing. *(Confirmed by the reviewer independently.)*

**Known-omitted Sleeper objects, ≥ 2 and stated as a floor:** `transactions` (no adapter; **layer 5
has no substrate because of it**) and **trending players** (named in the registry notes at
`source_registry.py:282-285`, recorded as never called in production by the 07-29 runtime trace).

### 3b. FantasyCalc — 1 stream

Unchanged from v1 and independently reproduced by the reviewer: pinned settings query hashed into
`SETTINGS_HASH` (`driver:31-32`); PK `(snapshot_date, source, settings_hash, player_key)`
(`store:45`); **append-immutable** via pre-write conflict check + `INSERT OR IGNORE`
(`:177-190,202-208`); content signature excludes `retrieved_at` (`:63-65`); three-state volatility
enum `captured | source_omitted | structurally_unavailable` (`:52-59`) — **the estate's best
missing-data discipline, and the pattern the declaration should propagate.**

Carried, unresolved, not re-litigated: the TW26Q correction that the ingested superflex feed is a
**scaled one-QB feed, not observed superflex trades.**

### 3c. nflreadpy — ≥ 6 objects across two pipelines

| `stream_id` | grain | window | consumed by |
| :-- | :-- | :-- | :-- |
| `nflreadpy/player_stats` | player × week | season window | **feature refresh AND realized-outcome scoring** |
| `nflreadpy/rosters` | player × roster × season | season window | feature refresh |
| `nflreadpy/snap_counts` | player × week | season window | feature refresh |
| `nflreadpy/pbp` | play | season window | feature refresh |
| `nflreadpy/participation` | play | **≥ 2019 only** (`:59`) | feature refresh — a different window from its four siblings, inside one collective hash |
| **`nflreadpy/schedules`** | game | per season | **realized-outcome scoring** (`run_realized_outcome_scoring.py:342`) — **absent from v1** |

Offseason boundary (feature refresh): the dynamic probe steps the ceiling down exactly once on a
source-load `ConnectionError` and otherwise **raises** — a >1-year gap is an outage, never a
fabricated season (`:69-92`). Good contract, declared only in a docstring.

### 3d. Realized-outcome scoring — the fourth pipeline

Weekly Mon 10:00 (`ops/launchd/com.davidleess.dynasty-realized-outcome-scoring.plist`), registered in
`report_freshness.json` with `timestamp_field=finished_at`, `status_field=status`,
`success_status=[ok, noop]`, `dormant_ok=true`, `tier=auxiliary`. **Its current marker reads
`status=noop`, `noop_reason=no_predictions_for_target`, `finished_at 2026-07-28T14:00:05Z`** — i.e.
it runs and correctly reports having nothing to score. It is a real pipeline over a real live stream
and v1 omitted it.

---

## §4 — Freshness detection: the file-newer-than-its-data condition

**Provenance unchanged: Tower established this by opening an artifact; Gemini's 2026-07-29 telemetry
is the earliest record of the shape in the repo. This section is corroboration and mechanism.**

Two health surfaces, different bases:

1. **`GET /api/system/capture-health`** reads **SQLite row dates**, never mtime
   (`system_capture_health_models.py:614-658`) — structurally immune. **Coverage, corrected:
   `capture_cadence.json` registers 2 stores, but `model_forward_capture` is produced by the
   downstream PVO/model-output capture path (`run_pvo_refresh.py:1-15`), which this document itself
   classifies as downstream. So it covers exactly ONE enumerated ingestion stream —
   `fc_forward_capture` — of ≥18.** v1's "2 of 17" is retracted.
2. **The report-freshness evaluator** (`system_health_models.py:439-480`) prefers the artifact's
   embedded timestamp, falls back to **file mtime** with the disclosure
   `timestamp_source:mtime_fallback` (`:464`), and treats a future timestamp as an anomaly rather
   than freshness (`:480`).

**Of the 8 registered artifacts, `pvo_refresh` alone declares neither a `timestamp_field` nor a
`status_field`** — independently confirmed by the reviewer, including that the evaluator really
reaches the mtime branch for it and really ignores its status. Verified on disk: mtime
`2026-07-29T13:30:26Z`; the data's own vintage is `capture_report.capture_date = 2026-07-29`
(**day granularity only**); a top-level `"status": "ok"` sits unread. **A touch, copy, restore or
partial rewrite advances the basis it is judged by, and its own status cannot contradict it.**

**What the declaration adds:** `observation_timestamp_field` (required, at the finest granularity
available — a date cannot answer a 26-hour question) · `producer_status_field` (required where the
artifact carries one) · `freshness_basis` materialized as `embedded | mtime_fallback`, never
inferred · and the consumer rule: **file mtime is never a freshness basis without an emitted
disclosure, and an mtime-vs-embedded divergence is itself reportable, not silently resolved toward
the newer value.**

**Detectable and declarable — not fixed.** `pvo_refresh` needs a `report_freshness.json` change plus
a producer question about emitting a finer timestamp. **Neither is opened here.**

---

## §5 — What this resolves of the open v4 findings (arithmetic corrected)

| Codex v4 finding | Status |
| :-- | :-- |
| **Blocking 3** — pipeline defined with no declaration contract | **Addressed** by §2 — and only after the v1 attempt failed on three real pipelines. |
| **Blocking 4** — 10 Sleeper endpoints compressed into one row | **Addressed** by §3a, one row per endpoint. |
| **Blocking 1** — §A contains a false row | **Untouched.** |
| **Blocking 2** — §A blind spots | **Untouched.** |
| **Blocking 5** — `B \| P \| O` not disjoint | **Untouched.** |
| **Material** — run record omits requests/pages/bytes and attempt identity | **Untouched.** |

**TWO of six addressed; FOUR open.** v1 said "three and three" while its own table showed two and
four. No revision to contract v4 has been authored.

---

## §6 — Registry drift: what is established, and what is NOT (corrected)

v1 called this "confirmed in both directions." **That was ahead of the evidence and is retracted.**

- **`nfl_data_py` vs `nflreadpy` — NOT a defect on this evidence.** The registry entry
  (`source_registry.py:95-107`) describes draft/age/outcome roles and is **not read by
  `run_feature_refresh`**. `docs/agent-ledger/2026-05-11.md:315-323` records the key as
  **intentionally retained per David's own scope confirmation**, alongside the
  `nfl_data_py_verified_nfl_draft` provenance string. Package-name inequality does not establish
  that the entry falsely names this runner. **A naming mismatch exists; a defect is not established,
  and David already ruled on the key.**
- **`sleeper` `freshness_hours=1` vs a daily job — CONDITIONAL, not confirmed.** v1 asserted a
  contradiction in §6 while §7 declared the semantics unresolved. **Those cannot both stand.** If
  `freshness_hours` means ingest interval, it contradicts the 09:20 daily job; **if it means cache
  TTL, there is no contradiction.** The finding is therefore *conditional on David's open §11
  question*, and is stated that way.
- **What IS established, and is the substantive point:** the registry's grain is **source**, so all
  11 Sleeper endpoints and all ≥6 nflreadpy objects are **inexpressible in it**. That is a
  structural fact about the container, independent of any naming question — and it is the real
  content of David's open question about where the declaration lives.

## §7 — Declared unknowns

1. **Per-endpoint Sleeper timeout/retry semantics** — none declared; whether the absence is
   intentional is `UNDECLARED`. Sharper after finding 2: two streams carry an unbounded request-time
   call rate with no declared timeout.
2. **`freshness_hours` semantics** — David's open question; §6's sleeper row depends on it.
3. **Late-data and backfill policy** — no stream declares one.
4. **Whether the two on-request-only streams should carry a cadence at all.**
5. **Whether ≥18/≥4 are the true totals.** The method establishes floors. A consumer outside the
   scheduled runners and adapter file would not have been found by it.

## §8 — The one question needed at landing, not at start

**Where does this declaration live** — an extension of `SOURCE_REGISTRY`, which §6 establishes
cannot express the unit, or a new declaration artifact? Unanswered, and it did not block the work.

*(The SQL governance job and the laptop-sleep policy are untouched by this document.)*
