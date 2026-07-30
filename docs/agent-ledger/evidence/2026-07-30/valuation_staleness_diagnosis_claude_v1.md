# Diagnosis — why the daily valuation republish advances its date while the model layer does not

**Claude Code, 2026-07-30. DIAGNOSIS ONLY.** Opened under TW30-LAYERS-J on David's word
*"focus on layers 1 and 2"*, absorbed into the enumeration thread by Tower.
**No producer touched, no repair, no config change, no adjacent thread. Read-only throughout.**

**Layer:** the defect **presents** at layer 3 (the published valuation) and **originates** at
layers 1–2. That is the finding, not an assumption — §2 traces it.

**All observations anchored to 2026-07-30, 11:20–11:35 ET**, after the day's 09:00–09:45 job cluster.
An unanchored on-disk claim went stale inside a frozen document earlier today; the rule is now applied.

**Provenance.** The fact that **the artifact reports its own staleness in a field nobody reads** is
**TOWER'S**, established by opening the artifact. What follows is corroboration and mechanism.
**It is worse than "unread," and that part is a finding of this diagnosis:** the one consumer that
parses the field **deliberately discards it** unless a separate tripwire has fired (§4).

---

## §1 — What is actually true right now

| Fact, as of 2026-07-30 ~11:30 ET | Value | Source |
| :-- | :-- | :-- |
| PVO runtime republished today | `source_as_of 2026-07-30T13:36:48Z` | `universe_pvo_runtime.ready.json` |
| Its own recorded seed age | **`seed_age_days = 33.8`**, `seed_as_of 2026-06-26T18:16:37Z` | same file, `seed_staleness` |
| Value drift vs that seed | **`mean_abs_value_delta = 0.0`, `p95_abs_value_delta = 0.0`, `count_players_drifted_gt_5pct = 0`** | same |
| Population drift vs that seed | `ENGINE_B −2`, `INACTIVE +2`, `PRE_MODEL +2` | same |
| Engine B feature runtime last changed | **2026-07-10 09:21** (20 days) | `engine_b_features_runtime.csv` mtime; report `generated_at 2026-07-10T13:21:15Z` |
| Feature-refresh job outcomes on record | **32 × `noop`, 1 × `ok`** | `app/data/logs/feature_refresh.out.log` — the entire file |
| League capture today | `run league-20260730T133616Z` | `league_capture.out.log` |

**So the model values are byte-for-byte the 2026-06-26 baseline, republished this morning with
today's timestamp.**

## §2 — The chain, established layer by layer

1. **Layer 1 — ingestion has nothing new to give.** The five nflreadpy frames are the season's
   completed data. No games have been played, so the frames are identical day over day. **This is
   correct upstream behavior, not a fault.**
2. **Layer 2 — curation therefore no-ops, BY DESIGN.** `feature_refresh_runner.py:101` returns a
   no-op when the collective source hash equals the last run's and the last status was not
   `blocked`. The log is unambiguous: **32 no-ops and a single `ok`**, the `ok` matching the
   2026-07-10 runtime rebuild. The runtime `runtime_sha256 88c52fc2…` in today's resolved feature
   source is the same hash the 07-10 report recorded.
3. **Layer 3 — the valuation rebuild runs anyway, and is deterministic.** `run_pvo_refresh.py`
   invokes exactly one allowed command (`build_universe_pvo_batch`, enforced at `:194-205`), which
   resolves the feature source once (`build_universe_pvo_batch.py:243-245`) and gets the **frozen
   07-10 runtime**. Same inputs + same frozen model artifact → **same outputs**, and the deltas of
   `0.0` are the arithmetic proof rather than an inference.
4. **The timestamp advances regardless.** `source_as_of` is stamped at write time by the producer.
   Nothing in that path compares content to the prior publication before stamping it.

**Conclusion: the foundation did not break. It is idling, correctly, and the layer above it
republishes that idle state with a fresh date.**

## §3 — What moves and what does not — the part that matters for the product thesis

| Lane | Moves daily? | Evidence |
| :-- | :-- | :-- |
| **Market (FantasyCalc)** | **YES** — captured 09:00, divergence refreshed 09:40 | `fc_forward_capture.out.log` 2026-07-30 09:00; divergence status `finished_at` today |
| **League/roster state (Sleeper)** | **YES** — a new immutable run every day | `league-20260730T133616Z`; the `−2/+2/+2` population deltas |
| **Model value (Engine B → DVS/PVO)** | **NO** — frozen at the 06-26 baseline | `mean_abs_value_delta = 0.0` for 33.8 days |

**The core product thesis is our-value-vs-market. Right now that margin has a moving denominator and
a static numerator:** every change in the divergence for 33 days has come from the market side alone.
The number is not wrong — it is arithmetically exact — but **anything read as "our model moved" is
market motion in a model-labelled frame.** Descriptive statement of fact; no claim about whether the
edge exists, which remains unvalidated.

## §4 — The disclosure that exists and is discarded (Tower's fact, mechanised)

The producer **does** compute its own staleness and writes it into the ready marker — `seed_age_days`,
the drift deltas, `promotion_review_threshold_crossed`, `review_triggers`. The pipeline is honest at
the point of production.

Three independent reasons it never reaches a reader:

1. **The registry does not look.** `report_freshness.json` registers `pvo_refresh` with
   **`timestamp_field: null` and `status_field: null`**, so the evaluator judges it by **file mtime**
   (`system_health_models.py:464`, disclosure `timestamp_source:mtime_fallback`). The file is
   rewritten daily, so it reads **fresh, every day, permanently**.
2. **The one consumer that parses the field discards it.** `what_changed/report.py:178-185` reads
   `seed_staleness` and then sets it to `None` unless **`promotion_review_threshold_crossed`** is
   true. In today's marker that flag is **`false`** — so a 33.8-day-old baseline with zero drift is
   *by construction* invisible on that surface. **Not merely unread: read, evaluated, and dropped.**
3. **Zero drift is exactly the state that suppresses the disclosure.** The tripwire is designed to
   fire on *large* drift. A pipeline that has stopped advancing produces *no* drift — so the
   condition that should raise "this has not moved in a month" is the same condition the surface
   treats as "nothing to report."

**That is the finding Tower asked for: the defect disclosed itself for weeks in a field whose only
consumer suppresses it precisely when the disclosure would matter most.**

## §5 — Consequences named, NOT opened

- **Aging is frozen with the features.** `age` is a materialized column in the feature CSV, so it
  advances only when features rebuild. No aging-curve movement has entered any value since 07-10.
  Whether it *should* advance between rebuilds is a **model-governance question under `00` §Aging
  Curves and the model-change governance ruling** — it is not mine to answer and I have not.
- **`00` §In-Season expressly supports stable off-season values** ("PVO remains stable until new
  in-season utilization accumulates"). **So the freeze itself is doctrinally correct**, and any
  proposal to make values move in the offseason would need to reckon with that ruling, not just with
  this diagnosis.
- **What is NOT doctrinally supported is the freshness presentation**: a daily-advancing timestamp,
  a health surface that reads it by mtime, and a self-disclosure that is suppressed. That is the
  layers-1–2 defect this diagnosis establishes.

## §6 — What this diagnosis did NOT establish

1. **Why the 07-10 run produced an `ok`** — one source-hash change 20 days ago, cause unexamined.
2. **Whether the source hash covers the right inputs.** It spans five nflreadpy frames only. Depth
   charts, team changes and injuries are **not ingested as streams at all** (the enumeration's
   omitted-stream finding), so they *cannot* trigger a rebuild regardless of the hash. Naming the
   gap is not a claim about what should feed it.
3. **Whether any consumer other than What-Changed would surface staleness if asked.** Not swept.
4. **Nothing about the front end.** Not read, not opened, not implicated by this document.

## §7 — The stopping point

Every remaining step is a **change**: registering `pvo_refresh` with its embedded timestamp and
status field; making the What-Changed suppression rule distinguish "no drift because stable" from
"no drift because frozen"; deciding whether an unmoved republish should stamp a new `source_as_of` at
all. **Each is a producer or config change and none is authorised. The diagnosis stops here.**
