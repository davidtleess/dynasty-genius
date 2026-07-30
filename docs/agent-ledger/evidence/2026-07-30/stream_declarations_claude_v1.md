# Stream Declarations — the three live sources, declared against real code — v1

**Authored by Claude Code, 2026-07-30.** David's word, verbatim: **"answer 1: do the enumeration."**
Thread opened by TW30-GO-G. Scope held by Tower: **declare the streams for the three live sources
against real code.** Nothing else is opened.

**This is declaration work, not investigation and not implementation.** No running job changes, no
dependency, no migration, no schema change, no repair of any defect named below. Where the code
disagrees with a prior claim of mine, the code wins and the claim is retracted in place.

**Layer:** primary **1–2** (ingestion + curation). No layers 1–2 dependency check is recorded,
because this work *is* at layers 1–2; there is nothing beneath it to check against.

**Evidence rule for every cell below:** traced to `file:line` in this repository and re-read today.
A cell I could not establish says **`UNDECLARED`** and names what would settle it. **Compressing
several unassessed things into one row is the failure this document exists to avoid** — that was
Codex's fourth blocking finding against contract v4, and it is the reason this artifact enumerates
one row per endpoint rather than one row per source.

---

## §1 — The declared unit set

Contract v4 §2 defines **stream** (one source object at one grain) and **pipeline** (one composite
load → build → publish unit) but gives the pipeline **no declaration contract** — Codex blocking
finding 3. §2 below supplies one. The units found live:

| Unit class | Count | Where established |
| :-- | --: | :-- |
| Sleeper streams (adapter endpoints) | **11** | `app/data/sleeper.py:15,22,29,36,43,50,57,64,71,78,85` |
| FantasyCalc streams | **1** | `src/dynasty_genius/capture/fc_forward_capture_driver.py:31` |
| nflreadpy streams | **5** | `scripts/run_feature_refresh.py:61-65` |
| **Live ingestion streams total** | **17** | — |
| Omitted stream (declared, never ingested) | **1** | Sleeper `transactions` — **no adapter function exists**; the 11 above do not include it |
| Ingestion pipelines | **3** | league capture · FC forward capture · feature refresh |
| Downstream publication pipelines (consume, do not ingest) | **2** | PVO refresh · market-divergence refresh |

**The "at least 17" of contract v4 §9 is confirmed as exactly 17 live ingestion streams** under the
stream definition in force. The count is not the contribution here — the per-row disposition is.

---

## §2 — NEW: what a pipeline must declare (Codex blocking finding 3)

A stream declares what arrives. A pipeline declares what is *done* with what arrived. Neither
substitutes for the other, and `write_disposition` belongs here rather than on the stream.

`pipeline_id` · `input_stream_ids` (the exact set, versioned) · `destination_identity` (the artifact
or table written) · `destination_key` (what makes a destination row/file unique) ·
`write_disposition` (append-immutable | replace-whole | merge-by-key) · `acceptance_record` (what
records that the write was accepted, and where) · `publication_decision` (what makes the output
servable, and what happens when it is not) · `failure_visibility` (the named status surface and its
path) · `replay_boundary` (extraction | normalization | derivation).

The three ingestion pipelines declared against that contract:

| Field | **league capture** | **FC forward capture** | **feature refresh** |
| :-- | :-- | :-- | :-- |
| `pipeline_id` | `league_capture` | `fc_forward_capture` | `feature_refresh` |
| Runner | `scripts/run_league_snapshot_capture.py` | `scripts/run_fc_forward_capture.py` | `scripts/run_feature_refresh.py` |
| Schedule | 09:20 local | 09:00 local | 09:15 local |
| `input_stream_ids` | 9 Sleeper endpoints (§3) | FantasyCalc `values/current` | 5 nflreadpy objects |
| `destination_identity` | immutable run dir `app/data/league_runtime/runs/<run_id>/` + 4 named artifacts | `fc_forward_capture.db`, two tables | one composite runtime candidate |
| `destination_key` | `run_id` (single path segment, traversal-rejected — `league_capture.py:53-55`) | `(snapshot_date, source, settings_hash, player_key)` — `fc_forward_capture_store.py:45` | whole-artifact replace; no row key |
| `write_disposition` | **replace-whole, run-immutable** | **append-immutable** | **replace-whole, hash-gated** |
| `acceptance_record` | ready marker written **last**, `os.replace` atomic — `league_capture.py:231-237` | row presence + `payload_hash` — `driver:222` | source hash over all five frames — `run_feature_refresh.py:236` |
| `publication_decision` | servable **iff** the marker names the run **and every named artifact re-hashes to the marker digest**; otherwise falls back to committed seeds and **never scans `runs/`** — `league_capture.py:5-7` | n/a (store is the destination) | `publish_runtime(...)` gated by integrity floors: non-empty candidate, all four positions present — `run_feature_refresh.py:43-44,240,243-244` |
| `failure_visibility` | `capture_status_latest.json` with named reason — `league_capture.py:31,67-88` | report at `app/data/capture/fc_forward_capture_latest_report.json` | status string on stdout + report artifact; exit 0 only on `ok`/`noop` — `:257-262` |
| `replay_boundary` | derivation (raw Sleeper payload not retained per-run) | normalization (`payload_hash` retained) | derivation (no repo-local raw) |

**The league-capture pipeline is the strongest ingestion contract in the estate** and is worth
naming as the model the others are measured against: immutable run identity, digest-verified
artifact set, marker-written-last, atomic pointer swap, fail-closed fallback to committed seeds, and
a named failure reason on a status surface. Contract v4's worked table dropped it entirely.

---

## §3 — Stream declarations

### 3a. Sleeper — 11 streams, one row each

`BASE_URL = https://api.sleeper.app/v1` (`app/data/sleeper.py:5`). No auth. Every function is a bare
`GET` through `_get` (`:8-12`) with **no retry, no backoff, and no explicit timeout** — the httpx
library default applies, undeclared anywhere. Established by reading the function body, true of all 11.

| # | `stream_id` | adapter | grain | lifecycle | delivery | in daily capture? | call site |
| --: | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| 1 | `sleeper/league_drafts` | `get_league_drafts:57` | draft × league | live | scheduled | ✅ | `build_sleeper_universe_snapshot.py:54` |
| 2 | `sleeper/league` | `get_league:29` | league | live | scheduled | ✅ | `:65` |
| 3 | `sleeper/rosters` | `get_rosters:36` | roster × league | live | scheduled | ✅ | `:66` |
| 4 | `sleeper/users` | `get_users:43` | user × league | live | scheduled | ✅ | `:67` |
| 5 | `sleeper/traded_picks` | `get_traded_picks:50` | pick × league | live | scheduled | ✅ | `:68` |
| 6 | `sleeper/players_nfl` | `get_all_players:78` | player | live | scheduled | ✅ | `:69` |
| 7 | `sleeper/nfl_state` | `get_nfl_state:85` | league-year singleton | live | scheduled | ✅ | `:70` |
| 8 | `sleeper/draft` | `get_draft:64` | draft | live | scheduled | ✅ | `:76` |
| 9 | `sleeper/draft_picks` | `get_draft_picks:71` | pick × draft | live | scheduled | ✅ | `:77` |
| 10 | `sleeper/user` | `get_user:15` | user | live | **on-request** | ❌ | `app/services/roster_auditor.py:415`, reached by `GET /api/roster/audit` (`app/api/routes/roster.py:14`) |
| 11 | `sleeper/leagues_for_user` | `get_leagues:22` | league × user × season | live | **on-request** | ❌ | `roster_auditor.py:424` |
| — | `sleeper/transactions` | **none — no adapter exists** | transaction | **omitted-stream** | — | ❌ | — |

**Two dispositions that are declarations, not defects to fix here:**

- **Streams 10–11 are live but unscheduled.** They execute on a David-facing API request, so their
  freshness is request-time and no cadence applies. `lifecycle=live` + `delivery=on-request` is the
  honest pair; one enum cannot hold it.
- **`transactions` is the omitted stream.** No adapter function exists for it, so this is absence at
  the adapter layer, not a disabled call. **Layer 5 (manager behavior) has no substrate because of
  it** — that is the census finding at `6c5c1ae`, restated here as a declared omission rather than a
  gap that vanishes into a field list. **Recorded, not opened.**

**Persistence, per stream:** streams 1–9 have **no independent persistence.** They are fetched,
composed into one snapshot by `build_snapshot()`, and only the composite is written
(`sleeper_universe_snapshot_latest.json`, `league_capture.py:39`). **A per-stream replay is
therefore impossible** — the replay boundary is derivation for all nine. Streams 10–11 persist
nothing at all.

### 3b. FantasyCalc — 1 stream

| Field | Value | Evidence |
| :-- | :-- | :-- |
| `stream_id` | `fantasycalc/values_current` | `fc_forward_capture_driver.py:31` |
| Endpoint | `values/current` with a **pinned settings query**, hashed into `SETTINGS_HASH` | `:31-32` |
| `grain` | player × snapshot_date × settings | `fc_forward_capture_store.py:45` |
| `primary_key` | `(snapshot_date, source, settings_hash, player_key)` | `:45` |
| `write_disposition` | **append-immutable.** `INSERT OR IGNORE` after an explicit pre-write conflict check; a changed value for an existing key **raises** rather than overwrites | `:177-190, 202-208` |
| Content signature | every stored column **except `retrieved_at`** — a same-day re-run with identical content is not a conflict, a changed value with a stale hash still is | `:63-65` |
| Missing-value fidelity | three-state enum: `captured` / `source_omitted` / `structurally_unavailable` — a bare NULL cannot distinguish "FantasyCalc published nothing" from "row predates the schema" | `:52-59` |
| `replay_boundary` | normalization (`payload_hash` retained, raw payload not) | `driver:222` |

**This is the estate's best missing-data discipline** and the declaration should propagate the
pattern, not just record it: the three-state enum is what stops a silent NULL becoming a fabricated
zero downstream.

**Carried forward, unresolved and NOT re-litigated here:** the TW26Q correction that the ingested
superflex feed is a **scaled one-QB feed, not observed superflex trades**. That is a semantic defect
in what this stream *means*, orthogonal to how it is captured, and it remains queued.

### 3c. nflreadpy — 5 streams

Loaded together by `_load_source` (`scripts/run_feature_refresh.py:47-66`; the package is imported
lazily at `:54` as `nflreadpy`), `nflreadpy==0.1.5`.

| `stream_id` | grain | window | note |
| :-- | :-- | :-- | :-- |
| `nflreadpy/player_stats` | player × week | full season window | base population for the join chain |
| `nflreadpy/rosters` | player × roster × season | full window | |
| `nflreadpy/snap_counts` | player × week | full window | |
| `nflreadpy/pbp` | **play** | full window | |
| `nflreadpy/participation` | **play** | **≥ 2019 only** — `:59` | a different season window from its four siblings, inside one composite hash |

- `schema_policy` = **partial, established.** The assembly directly indexes required columns, so a
  missing required column aborts the batch; extras are ignored.
- `delete_behavior` = **partial, established.** `player_stats` is the base; missing roster/snap/PBP
  rows propagate through explicit joins and the next accepted runtime replaces the prior whole
  output.
- **Offseason boundary is declared and fail-closed:** the dynamic window probe steps the ceiling
  down exactly once on a source-load `ConnectionError`, and if neither year loads it **raises** — a
  >1-year gap is treated as a genuine upstream outage, never a fabricated season
  (`:69-92`). This is a good contract and it is currently undeclared anywhere but the docstring.

---

## §4 — Freshness detection: the file-newer-than-its-data condition

**Provenance, stated plainly: Tower established this condition by opening an artifact rather than
reading a summary, and asked whether the declaration can detect it. What follows is corroboration
and mechanism, not an independent discovery by this lane.** The earliest record of the shape in the
repo is **Gemini's 2026-07-29 telemetry**, which flagged `league_opportunity_latest.json` as
"Stale (Mtime 2026-07-23, content 2026-07-15)"; my own 08:05 read today carries the same numbers.

**The mechanism, traced.** Two independent health surfaces exist and they use different bases:

1. **`GET /api/system/capture-health`** reads **row dates inside the SQLite stores**, never file
   mtime (`system_capture_health_models.py:614-658`). It is structurally immune to this condition —
   **but it registers only 2 stores** (`fc_forward_capture`, `model_forward_capture` in
   `app/config/capture_cadence.json`). **It covers 2 of the 17 streams and none of the JSON
   artifacts.**
2. **The report-freshness evaluator** (`system_health_models.py:439-470`) prefers the artifact's
   **embedded timestamp** when one is registered, and falls back to **file mtime** when none is,
   emitting the disclosure `timestamp_source:mtime_fallback` (`:464`). It also guards against a
   future timestamp as an anomaly rather than freshness (`:480`).

**So the condition is detectable exactly where a `timestamp_field` is declared, and invisible where
it is not.** Of the 8 artifacts in `app/config/report_freshness.json`, **7 declare one. One does
not:**

| Artifact | `timestamp_field` | `status_field` | Consequence |
| :-- | :-- | :-- | :-- |
| `pvo_refresh` → `app/data/model_capture/pvo_refresh_latest_report.json` | **null** | **null** | freshness judged by **mtime**; and the file's own `"status": "ok"` field **is not read** |

Verified by opening that file today: mtime `2026-07-29T13:30:26Z`, while the data's own vintage
lives at `capture_report.capture_date = 2026-07-29` (**day granularity only**) and a top-level
`status` the registry ignores. **A `touch`, a copy, a restore, or a partial rewrite advances the
basis this artifact is judged by, and its own status field cannot contradict it.** This is the shape
Tower described, in the registered surface, on the PVO producer.

**What the declaration says about it — three fields and one consumer rule:**

- `observation_timestamp_field` — **required per published artifact**: where the *data's own* as-of
  lives, at the finest granularity available. A day-granularity date is declared as such, because
  "2026-07-29" cannot answer a 26-hour question.
- `producer_status_field` — required when the artifact carries one. An artifact that reports its own
  failure while the registry reads only its mtime is the silent-failure case in miniature.
- `freshness_basis` — one of `embedded` | `mtime_fallback`, **materialized in the output**, never
  inferred. The shipped evaluator already emits this disclosure; the declaration makes it a
  first-class declared property rather than a side effect.
- **Consumer rule:** *file mtime is never a freshness basis without an emitted disclosure, and a
  divergence between mtime and the embedded observation timestamp is itself a reportable condition,
  not a tie broken silently in favour of the newer one.*

**Named honestly:** the declaration makes this condition **detectable and declarable**. It does not
fix `pvo_refresh` — that is a config change to `report_freshness.json` plus a producer question
about emitting a finer-grained timestamp, and **neither is opened here.**

---

## §5 — What this resolves of the open v4 findings, and what it does not

| Codex v4 finding | Status after this enumeration |
| :-- | :-- |
| **Blocking 3** — pipeline defined with no declaration contract | **Addressed** by §2, and exercised against three real pipelines rather than asserted. |
| **Blocking 4** — "zero unknowns" was a token count; 10 Sleeper endpoints compressed into one row | **Addressed** by §3a: 11 rows, one per endpoint, each with grain, lifecycle, delivery, call site, and persistence. |
| **Blocking 5** — `B \| P \| O` not disjoint | **Untouched.** No mechanism classification is used in this document; the field remains unfixed in the contract. |
| **Blocking 1** — §A regression ledger contains a false row | **Untouched.** No amendment authored. |
| **Blocking 2** — §A is not complete enough to catch what it exists to catch | **Untouched.** |
| **Material** — restored run record omits requests/pages/bytes and attempt identity | **Untouched.** |

**Three of six addressed with evidence; three remain open and no revision to contract v4 has been
authored.** The retirement's own open findings are likewise untouched.

## §6 — Registry drift, confirmed in both directions

The census claim that `SOURCE_REGISTRY` "fails in both directions" is confirmed against
`src/dynasty_genius/sources/source_registry.py`:

- **Names a source that does not run as named:** `nfl_data_py` (`:95`, `freshness_hours=168`) — the
  live runner imports **`nflreadpy`** (`run_feature_refresh.py:56`), a different package. Two other
  entries carry the `nflreadpy_*` name, so the estate holds both vocabularies at once.
- **Declares a cadence its own job contradicts:** `sleeper` (`:274-279`) declares
  `freshness_hours=1` against a **once-daily** 09:20 capture. Contract v4 named this; it is
  re-verified here.
- **Omits the unit entirely:** the registry's grain is *source*, so all 11 Sleeper endpoints and all
  5 nflreadpy objects are invisible in it. **The registry cannot express the unit this declaration
  is built on** — which is the substance of David's open question about where the declaration lives.

## §7 — Declared unknowns

Named as unknown rather than compressed:

1. **Per-endpoint Sleeper timeout/retry semantics** — none declared in the adapter; whether the
   absence is intentional is `UNDECLARED`. Settled by a David or reviewer ruling, not by more reading.
2. **`freshness_hours` semantics** (ingest interval vs cache TTL) — still David's open question; the
   `sleeper=1` row cannot be interpreted without it.
3. **Late-data and backfill policy for every one of the 17 streams** — no stream declares one.
4. **Whether the two on-request Sleeper streams should carry a cadence at all** — a genuine design
   question, not an omission.

## §8 — The one question that blocks landing, not starting

**Where does this declaration live** — an extension of `SOURCE_REGISTRY` (which cannot express
streams, per §6) or a new declaration artifact? Work proceeded without the answer, as scoped. It is
needed at landing, and only then.

*(David's other open items — the SQL governance job and the laptop-sleep policy — are untouched by
this document.)*
