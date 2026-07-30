# Framing — the three scheduling defects (TW30-SCHED-S)

**Claude Code. Written 2026-07-30 12:30:43 EDT** *(machine clock, pasted — Tower's binding anchor rule).*
**Authority:** David, verbatim: *"yea fix those scheduling problems."* This is the first authorisation
today touching his machine's schedules. **Framing artifact — no RED yet, no plist authored, nothing
loaded.**

**Layer:** 1–2. **Boundaries held:** scheduling only. **No producer, model, SQL, or
artifact-under-review is touched.** Nothing is loaded onto his machine by this document.

---

## §1 — What the two unscheduled reports are FOR, and whether weekly is right

*(Tower asked for this explicitly rather than as an assumption.)*

**`roster_capacity` → `scripts/run_roster_capacity_audit.py`.** A read-only capacity simulator: it
scores roster-construction scenarios against the current PVO and Sleeper snapshot and writes one
gitignored scorecard. It answers *"what does my roster's shape cost me, and what would change if I
cut/added?"*

**Its scheduler absence was DESIGNED, not overlooked.** The producer's own docstring says: *"No API
route, no scheduler plist in v1 (David-gated)."* v1 deliberately left the scheduler as a separate
David word. **That word has now been given.** This matters for the record: the gap is a deferred
decision now resolved, not negligence.

**`league_opportunity` → `scripts/build_league_opportunity_map.py`.** Phase 17.5: it joins league
state against the market-divergence overlay to surface where trade opportunity sits across the
twelve rosters. It answers *"who in my league is holding something I want, at a price the market
disagrees with?"*

**It is not a standalone producer — it is the last step of a chain.** It appears as PhaseStep 17.5 in
`refresh_league_intelligence.py`, after league capture (17.1), the PVO batch (17.2), the value matrix
(17.3), posture (18.3) and market divergence (17.4). It consumes their outputs.

**Cadence — recommendation, explicitly not a decision:**

| Report | Registered | What its inputs actually do | Recommendation |
| :-- | :-- | :-- | :-- |
| `league_opportunity` | **weekly** | market divergence refreshes **daily**; league/roster state changes **daily** | **Weekly is wrong for it.** Its answer can change every day, and a weekly artifact silently presents a stale answer as current. **Daily, chained after its dependencies.** |
| `roster_capacity` | **weekly** | changes on transactions — daily in-season, rare in the off-season | **Weekly is defensible but season-blind.** `02`'s compounding lens requires season-aware cadence. **Daily in-season; weekly off-season** is the honest shape. |

**Under David's own content-basis ruling this recommendation is cheap to accept:** running more often
costs little when an unchanged artifact reports `unchanged_expected` rather than pretending freshness.
**Cadence is his call; this is the input, not the answer.**

## §2 — The defect underneath all three problems

**The morning cluster is a DEPENDENCY GRAPH ENCODED AS WALL-CLOCK OFFSETS.** 09:00 FC → 09:15
features → 09:20 league capture → 09:30 PVO → 09:35 league opportunity (registered) → 09:40 market
divergence → 09:45 what-changed.

Two consequences, one already named by Tower and one found while framing this:

1. **Named:** PVO at 09:30 starts while the 09:15 feature job may still be running, so it consumes
   yesterday's features **by construction**.
2. **FOUND HERE, and it is the same defect:** `league_opportunity` is registered at **09:35** while
   **market divergence — which it consumes — runs at 09:40.** Scheduling it at its registered time
   would bake in a one-day-stale overlay on day one. **A fix that only moves clock numbers would ship
   this defect while claiming to remove it.**

**This is why a fixed offset is the wrong answer** — not merely fragile, but because the estate
already contains a dependency-ordered executor and the clock times are a lossy re-encoding of it.

## §3 — Problem 2: dependency ordering — options, with the tradeoffs stated

| Option | Mechanism (all already in-repo) | Cost / risk |
| :-- | :-- | :-- |
| **A. Chain in one job** | A launchd job runs a sequence — the pattern `refresh_league_intelligence.py` already implements (`PhaseStep` + subprocess, dependency order) | Couples the steps: an early failure stops later steps. **May be correct** (why publish an opportunity map from a failed capture?) but it changes failure semantics and would need the silent-failure paths already recorded to be considered. |
| **B. launchd `WatchPaths`** | Trigger the dependent job when the upstream's ready marker changes | True dependency ordering — **but the feature job no-ops most days**, so a watch-triggered PVO would stop running daily. **PVO also performs the daily model-output PIT capture**, which is a compounding asset; stopping it daily is a product decision, not a scheduling one. |
| **C. Fixed later offset** | Move PVO to a later clock time | **The defect with a longer fuse.** The upstream duration is dominated by network I/O and varies; the offset that works in the off-season may not survive a live-data morning. |

**Recommendation: Option A**, because it is the only one that expresses the dependency *as* a
dependency using a pattern the repo already ships, and because it does not silently change how often
the PIT capture accrues. **Option B is genuinely attractive and I am not dismissing it** — it is
strictly better on ordering, and worse only because of a coupling to the daily capture that is
David's to weigh, not mine.

**If David prefers C**, the honest offset reasoning is: no measured duration exists for the feature
job (the log records outcomes, not timings), so any offset would be chosen without evidence. **That
is the argument against C, and it is an evidence gap rather than an opinion.**

## §4 — Problem 3: the mtime fallback CANNOT be fixed by configuration alone

**Measured, not assumed:**

- The registry loader reads **top-level keys only** — `payload.get(artifact.timestamp_field)`
  (`system_health_models.py:602`). No dotted-path support exists.
- `pvo_refresh_latest_report.json` has **no top-level timestamp**. Its only top-level scalars are
  `status`, `decision_supported`, `commit_required_for_repo_baseline`.
- A real content timestamp **does** exist — **`capture_report.artifact_vintage`**
  (`2026-07-30T13:36:37.307475+00:00`, read 2026-07-30 12:30:43 EDT) — **nested one level down.** Alongside it sit
  `artifact_sha256`, `semantic_output_hash`, `artifact_age_days` and `vintage_changed` — i.e. the
  producer already computes exactly what David's content-basis ruling asks for.

**So "point it at a real content field" has two possible mechanisms and BOTH exceed a config edit:**

- **(i) Teach the loader dotted paths** (`capture_report.artifact_vintage`). Touches
  `system_health_models.py` — health/reader code, **not** a producer. Smallest honest change.
- **(ii) Have the producer emit a top-level mirror.** **OUT OF BOUNDS** — producers are excluded by
  this authorisation.

**I am not choosing.** (i) is the only in-bounds mechanism I can see, and it is a code change beyond
"scheduling", so it needs Tower's ruling on scope before a RED is written for it. **Stated rather
than quietly done.**

**Also worth David's attention, not opened:** `status` is a real top-level field and
`status_field` is **null** for this artifact — so the registry ignores a producer-reported failure it
could already read **with no code change at all.** That part IS config-only.

## §5 — Falsification seeds for the RED

1. A plist that parses but names a **path that does not exist** (the failure Tower called worse than
   absence).
2. **Two jobs firing for one artifact** — a new job plus an existing orchestrator step for
   `league_opportunity`.
3. A job whose `Label` collides with an already-loaded label.
4. A chained job where an **early failure leaves later steps silently unrun** with no structured record.
5. `WatchPaths` firing on a **no-op rewrite** (or failing to fire when no rewrite occurs).
6. A registry `timestamp_field` pointed at a **nested path the loader cannot read** — which would read
   as `corrupt_or_empty`/`unknown` rather than working.
7. Cadence declared **weekly** while the job fires **daily** — the declaration and the scheduler
   disagreeing is the same class of defect as the aim/target mismatch found this morning.

## §6 — Overclaim check

Nothing here makes any artifact fresher or any answer more correct. It makes two reports **run**, one
chain **ordered**, and one freshness signal **honest**. **No decision-grade claim is created, and
`decision_supported=False` is untouched throughout.**

## §7 — What I am asking for before any RED

1. **Tower's ruling on §4:** is a loader change (i) inside "fix the scheduling problems", or does
   problem 3 stop at the config-only `status_field` part and route the rest to David?
2. **David's call on §3** — A, B, or C — since B trades ordering correctness against daily PIT
   accrual, and that is his product decision.
3. **David's call on §1 cadence** — the registrations say weekly; the evidence says daily for one and
   season-aware for the other.
