# Layers 1–2 Census — Claude lane, v1

**Opened by David, 2026-07-29:** *"run the census."* His four axes:
**what we ingest · what is missing · what is stale · what is silently a constant.**

**FINDINGS ONLY.** Nothing here authorises a repair, spec, schema change, ingestion, schedule change,
or commit. Where the census implies work, it is named as **implied work** and stopped there
(`05` §3 — a conclusion is not a licence to fix).

**Scope:** layers 1–2 only — sources through curated stores. Models, analysis, and front-end are out.

---

# 1. COVERAGE — read this before any finding

*This section exists because the previous artifact never stated how much of the foundation it
examined, which let four probes read like an inventory. A census that does not bound itself is worse
than a smaller one that does.*

## 1.1 What was examined, and by what method

| Route | Method | Extent |
| :-- | :-- | :-- |
| **A — schedulers** | All 10 loaded LaunchAgents read from their plists; each traced into the script it runs | 10/10 |
| **B — served API** | `app/main.py` transitive import closure | 66 project modules |
| **C — mechanical sweep** | Host-string, HTTP-client, data-library, and sqlite-connect grep | `src/`, `app/`, `scripts/` |
| **D — declared registry** | `src/dynasty_genius/sources/source_registry.py` read and instantiated | 19 declared sources |
| **E — staleness** | **Delegated to the Operations & Telemetry lane** (see §1.3) | 30 artifacts, 10 jobs |

## 1.2 What this method structurally CANNOT see

- **Dynamically-constructed endpoints.** A host assembled at runtime from parts is invisible to a
  string sweep. Nothing suggests this exists here; it is not excluded.
- **Reachable ≠ executed.** Import-closure reachability **over**-approximates: a module in a closure
  may never run. Every "live" claim below is therefore corroborated against job logs, not left on
  reachability alone.
- **Untracked local activity.** Proven real today: a live Sleeper transactions probe on 2026-07-06
  exists in the ledger and left **no trace in code**. No repository method can see that class.
- **Runtime behaviour of external APIs.** What a source *offers* (the "what is missing" axis) is
  answered from adapters and payload shapes on disk, not by interrogating live APIs — no credentialed
  or rate-consuming calls were made.

## 1.3 Provenance of the staleness axis

The staleness axis was produced by the **Operations & Telemetry lane**, not by me. It arrived
**appended to `docs/agent-ledger/2026-07-29.md` (11:31 ET), not as a file under this evidence
directory** — that lane is barred from native file writes and its only sanctioned write surface is
the path-locked ledger append. **That is its charter working correctly, not a delivery failure.**
Figures attributed to it below are marked **[TEL]**; I verified the backup marker myself and it
matched exactly.

## 1.4 What is NOT assessed — first-class, never silently dropped

| Item | Status | Why |
| :-- | :-- | :-- |
| **Databricks / `gen_alpha.gold.*`** | **ENUMERATED — NOT ASSESSED. NEEDS DAVID'S WORD.** | Requires credentialed spend. Deliberately not spent. Tower is putting this in front of David directly. |
| **The independent second enumeration** | **COMPLETE — and the diff went against my method. See §1.5.** | Its artifact: `tw29_census_codex_runtime_trace.md` (SHA-256 `ca1e1a90…8586a2e6`, verified by me). |
| **8 of 11 external hosts** | **ENUMERATED — depth-limited** | Established as unreachable from anything scheduled; their internal behaviour was not assessed. |
| **"What the source offers that we do not take"** | **PARTIAL** | Answered for Sleeper from an on-disk payload. **Not answered for FantasyCalc or nflreadpy.** |
| **Constants sweep** | **PARTIAL — see §6** | One regex pattern over `src`+`app`. Its blind spots are enumerated there. |
| `app/data/realized_outcome/scorecard_latest.json` | **DOES NOT EXIST** [TEL] | See finding S-4. |

## 1.5 THE TWO-LIST DIFF — run, and it went against my method

The census deliberately used **two independent enumerations by different methods**, then diffed them,
rather than one enumeration plus a review — because a reviewer auditing my list inherits my blind
spot. **The instrument worked, and it found five holes in mine and none established in the other.**

**Established by the runtime-trace lane, ABSENT from my enumeration:**

1. **DynastyProcess archive / FantasyPros ECR** — a *sibling Git history* supplying `values.csv` and
   `db_playerids.csv`; **2,185 rows** in SQLite. **Root cause of my miss: my sweep was HOST-STRING
   based, and a source read out of a git history has no host string.** My method could not see this
   class in principle.
2. **First-party / manual identity and league inputs** — league context, college alias bridge,
   prospect registry, prospect-to-NFL bridge, the frozen 2025 bundle, `ff_playerids` pins. **My
   enumeration was oriented at *external* sources, so an entire class of first-party inputs was
   structurally invisible to it.**
3. **RAS / RotoViz / Campus2Canton** as fixture-backed adapters with real code paths — I had them
   only as registry names.
4. **PFF as an established *derived* source** — PFF-derived college YPRR is present for 336/874 rows.
   I had the host, classified it not-reachable, and was right about the HTTP path and wrong about
   whether the source is in the foundation.
5. **Sleeper CDN** — a 261-entry asset manifest. I enumerated the host and dismissed it as a one-off.

**In my enumeration and not the other: no true hole established.** Spotrac and NFL.com were the
candidates; the other lane covers them and resolves them *better* — references inside the frozen-2025
manifest with only the manifest stored, therefore **not** established ingests.

**Consequence for this document, stated rather than buried: §2's external-source enumeration is
INCOMPLETE as a census of everything the product ingests.** It is accurate about *external HTTP
sources reachable from scheduled jobs and the API* — which is what its method could establish — and
that is a narrower claim than "what we ingest." The other lane's matrix is the more complete
enumeration and should be read alongside this one.

**The one numeric divergence is RESOLVED, and neither measurement was wrong.** The draft-capital join
reads **373/501** by my probe and **375/505** by theirs because the two probes count **different
populations**:

- **375/505** — `app/data/training/engine_b_features_v2.csv` filtered to the latest `feature_season`
  (2025), joined `player_id → prospects_with_outcomes_v3.csv.gsis_id`.
- **373/501** — `app/data/valuation_runtime/universe_pvo_runtime.json`
  (`captured_at 2026-07-29T13:30:09Z`), selecting `valuation.engine_path == "ENGINE_B"`, same join and
  predicate.

The populations intersect on **498 IDs**. Seven latest-season CSV IDs are absent from the served
Engine B set (**two** of them carrying qualifying draft capital); three served IDs are absent from the
CSV population (**none** carrying it). That mechanically explains **505→501** and **375→373**.

**Both are exact and they must not be presented against the same denominator.** The training-store
figure describes what Engine B was *fitted on*; the runtime figure describes what is *served to
David*. **For the question this census asks — what reaches the surface — 373/501 is the relevant
one.**

**Scope reconciliation also confirmed:** their F5 (no unmeasured numeric constant at layers 1–2) and
my C-1 (`activity_recency_score = 0.0` at layer 5) **both stand** — different populations, and F5 does
not clear C-1. And they confirmed no correction to the Delta A/B attribution above.

---

# 2. THE ENUMERATION — what the product actually ingests

## 2.1 External sources: 11 present in code, **3 reachable from anything that runs**

**Established**, by import closure from all nine real entry points, each corroborated by job logs.

| Source | Reached by | Status |
| :-- | :-- | :-- |
| **FantasyCalc** (`api.fantasycalc.com`) | fc-snapshot 09:00; market-divergence 09:40; served API | **LIVE — daily** |
| **Sleeper** (`api.sleeper.app`) | league-capture 09:20; served API | **LIVE — daily** |
| **nflreadpy** (library) | feature-refresh 09:15; realized-outcome Tue; served API | **LIVE — daily, source-hash-gated** |
| CFBD, PlayerProfiler, Spotrac, PFF, NFL.com, SleeperCDN, Databricks, MyFantasyLeague | one-off scripts only | **NOT reachable from any scheduled job or the API** |

**Rerun:** transitive import closure over `scripts/run_*.py` + `app/main.py`, testing each closure's
modules for the 11 host strings. *(Two defects in my own closure tool were found and fixed before any
result was reported: a `src.`-prefix alias gap that hid FantasyCalc from its own capture job, and an
unfollowed `from pkg import submodule` form that collapsed the API from 66 modules to 2.)*

## 2.1b CONSOLIDATED SOURCE LIST — both lanes merged, so this is the one census to read

§2.1 is my method's answer (external HTTP sources reachable from schedulers and the API). **This
table is the union of both enumerations** and supersedes §2.1 as the census's answer to *"what does
the product ingest."* Rows marked **[RT]** were established by the runtime-trace lane and were
**missing from mine**.

| Source | Status | Notes |
| :-- | :-- | :-- |
| **Sleeper API** | **LIVE, daily** | 11 endpoints; 12,203 player rows; 6 curated player attributes |
| **FantasyCalc** | **LIVE, daily** | market values; 16,718 append-only rows at player-date-settings grain |
| **nflverse via `nflreadpy`** | **LIVE, daily** | source-hash-gated; Engine B store 2,741 player-season rows |
| **CFBD** | established, manual | college enrichment; large local cache families |
| **DynastyProcess / FantasyPros ECR** | **[RT]** established, historical | **read from a sibling *git history***, not an HTTP host — invisible to my method by construction; 2,185 rows, four snapshot dates |
| **PFF manual exports** | **[RT]** established, derived | college YPRR present for 336/874 rows; raw exports private and absent by design |
| **PlayerProfiler** | **[RT]** historical only | current probe artifact is **874/874 `parse_error`**; a working present-day feed is NOT established |
| **Sleeper CDN** | **[RT]** established | 261-entry player-asset manifest |
| **First-party / manual identity + league inputs** | **[RT]** established | league context, alias bridge, prospect registry, prospect→NFL bridge, frozen 2025 bundle, `ff_playerids` pins. **Not represented in the source registry at all** |
| **MFL rookie ADP** | executable, **production ingestion NOT established** | adapter callable; no local cache or output found |
| **RAS · RotoViz · Campus2Canton** | **[RT]** fixture-only | adapters read `resources/fixtures/*_mock.csv`; no production export found |
| **Spotrac · NFL.com** | **references, not ingests** | named inside the frozen-2025 source manifest; only the manifest is stored, no fetched contents |
| **Databricks Bronze/Silver/Gold** | **ENUMERATED — NOT ASSESSED** | needs David's word; no spend taken |
| Dynasty Data Lab · Dynasty Nerds · KTC · Sportradar · Genius Sports · Stats Perform · Rolling Insights | registry-declared, **not ingested** | no production boundary or store found for any |

**Two consequences worth stating plainly.** First, **the live daily surface is still three sources** —
that finding survives the merge. Second, the foundation is **wider and more manual** than either the
registry or my enumeration suggested: a git-history archive, private PFF exports, and a class of
hand-maintained first-party identity inputs all feed layers 1–2 without appearing in the declared
registry.

## 2.2 Local persistent stores

| Store | Size | Character |
| :-- | --: | :-- |
| `app/data/model_forward_capture.db` | **656 MB** | accumulating model PIT capture |
| `app/data/market_divergence_history.db` | **449 MB** | accumulating market PIT capture |
| `app/data/fc_forward_capture.db` | 9.1 MB | FantasyCalc forward capture |
| `app/data/fc_snapshots.db` | 2.0 MB | FantasyCalc snapshots |
| `app/data/league_runtime/runs/` | 78 files | per-run league snapshots, immutable by run id |
| `app/data/training/*.csv` | — | Engine A / Engine B training sets |

Over **1.1 GB** of accumulated point-in-time capture exists. **This is the part of the foundation
that is working as designed** — capture-and-accumulate rather than overwrite-`_latest`.

---

# 3. AXIS — WHAT WE INGEST (grain and cadence)

| Source | What arrives | Grain | Observed cadence |
| :-- | :-- | :-- | :-- |
| **Sleeper** | player universe + league/roster/user state | **6 attributes per player**: `age`, `full_name`, `position`, `sleeper_status`, `team`, `years_exp`; 12,203 players | daily 09:20 |
| **FantasyCalc** | market values | per-player market value + `retrieved_at` | daily 09:00 |
| **nflreadpy** | season stats → Engine B features | 33 feature columns | daily 09:15, **noop when source hash unchanged** |

**Sleeper endpoints called (11):** `/user/{username}` · `/user/{id}/leagues/nfl/{season}` ·
`/league/{id}` · `/league/{id}/rosters` · `/league/{id}/users` · `/league/{id}/traded_picks` ·
`/league/{id}/drafts` · `/draft/{id}` · `/draft/{id}/picks` · `/players/nfl` · `/state/nfl`.

---

# 4. AXIS — WHAT IS MISSING

**Method rule applied throughout, because its omission broke the previous artifact:** absence is
**never** concluded from the place I expected the data to be. Every claim below required a search of
everywhere the data class could live, and a join attempt where a join was possible.

## M-1. Transaction history — never ingested. **ESTABLISHED.**

`/league/{league_id}/transactions/{round}` is **not among the 11 Sleeper endpoints called**. No
implementation, no persisted transaction stream, no consumer exists in tracked code or reachable
history.

This is the single richest behavioural source in the league — every trade, waiver claim and
free-agent add — and it is **layer 5's entire substrate** (David: *"we can see manager behavior and
specific data trends of the 12 teams in this league"*). Its absence is the direct cause of finding
C-1 below.

**Bounded:** a live probe of this endpoint **was** run on 2026-07-06 (durable ledger record) and left
no code behind. "Never ingested" is established for the product; "never called" is false.

## M-2. Draft capital — ingested, **not joined**. **ESTABLISHED, and it corrects my own earlier claim.**

`prospects_with_outcomes_v3.csv` carries `pick`, `round`, `nfl_pick`, `nfl_round` with provenance
companions, from `nfl_data_py`. **373 of the 501 served Engine B rows join to it on `gsis_id` with
non-null pick AND round — and are served blank anyway.**

Root: `pvo_assembler.py:501-503` materializes the draft fields **only** from
`features["pick"]/["round"]/["draft_class"]`, and the active producer never joins the rookie table
into that feature dict. **This is a layer-2 join/materialization gap, not a layer-1 ingestion gap.**

**128 of 501 did not join and their root is NOT established. The population is mixed.**

*(I originally filed this as a layer-1 hole. It is not. I checked the two places I expected the data
and concluded absence without searching elsewhere — the exact error `05` §4 records. The refutation
came from the review lane and I reproduced it before conceding.)*

## M-3. Sleeper's payload is narrowed to 6 fields. **ESTABLISHED as fact; sufficiency NOT assessed.**

The live snapshot carries 6 attributes per player. Whether Sleeper offers more that we decline is
**not established** — answering it needs a live API schema read.

---

# 5. AXIS — WHAT IS STALE

**No staleness claim is made without a declared cadence.** Where none exists, the finding is
**"no declared cadence"** — not "fresh".

## S-1. Scheduled jobs slip, and 2026-07-27 was NOT unique. **[TEL], and it refines my own finding.**

| Date | Pattern |
| :-- | :-- |
| **2026-07-17** | FC snapshot, league capture, PVO refresh, backup **all late together ~11:42 EDT** (~2h 22m) |
| 2026-07-20 | backup 11m late |
| 2026-07-23 | backup fired **three times** — two unscheduled catch-ups plus the on-time run |
| **2026-07-27** | league capture, PVO refresh, backup **all late together ~19:31 EDT** (~10h) |

I had established the 07-27 slip and explicitly recorded that I had **not** established whether it
was the only such day. **It was not.** The telemetry lane independently reproduced my narrowing of
the 07-27 window (FC snapshot on time at 09:00, everything after 09:20 late) and found the recurring
pattern I had not looked for.

**The finding is therefore not an incident but a property: the schedule is best-effort and slips
silently whenever the host sleeps.**

## S-2. `_latest` pointers that stopped advancing. **[TEL]**

| Artifact | Internal timestamp | Age at census |
| :-- | :-- | --: |
| `app/data/valuation/universe_pvo_latest.json` | 2026-06-26 | **33 days** |
| `app/data/valuation/roster_cut_report_latest.json` | 2026-06-23 | **36 days** |
| `app/data/valuation/team_posture_latest.json` | 2026-06-23 | **36 days** |
| `app/data/valuation/team_value_matrix_latest.json` | 2026-06-23 | **36 days** |
| `app/data/valuation/league_opportunity_latest.json` | 2026-07-15 | **14 days** |
| `app/data/roster_capacity/roster_capacity_latest.json` | 2026-07-15 | **14 days** |
| `app/data/features_runtime/*` | 2026-07-10 | **19 days** |

The live pipeline writes to `valuation_runtime/` and `league_runtime/runs/`, which are **fresh
today**. These `valuation/*_latest` files are a **parallel, no-longer-advancing generation**.
**Whether any live surface still reads them is NOT established** — it needs a call-path trace and is
named as implied work, not opened.

## S-3. Artifacts with no internal timestamp — **"no declared cadence" cases.** [TEL]

`universe_pvo_coverage_runtime.json` · `universe_market_divergence_coverage_latest.json` ·
`league_runtime/runs/*/coverage.json` · `universe_pvo_coverage_latest.json` ·
`draft_pick_value_curve_v1.json`. Freshness for these is **not measurable**, only inferable from
mtime. Recorded as a gap, not scored.

## S-4. A scheduled job declares an output path that does not exist. **[TEL] + verified**

`com.davidleess.dynasty-realized-outcome-scoring` runs Tuesdays with
`--report-path app/data/realized_outcome/scorecard_latest.json`. **That file and its directory do not
exist.** Consistent with all three logged runs returning `noop / no_predictions_for_target` — the job
runs, produces nothing, and exits 0.

## S-5. Backup — healthy, and independently verified by me.

Run `20260729T141500Z`, started `14:15:00.144666Z` **on schedule**, finished `15:22:59.401919Z`,
**306 files, 1,293,152,815 bytes, `failures: []`, `sha256_verified: true`.** I read the marker myself
rather than accepting the relayed figures; they matched exactly.

**Separately proved today:** a **restore drill** pulled 267 objects (120 MB) back out of the 07-28
backup — 266 byte-identical to local, the 267th proved faithful by its stored `Content-Length`.
Backup coverage is **demonstrated, not asserted**.

---

# 6. AXIS — WHAT IS SILENTLY A CONSTANT

## C-1. `activity_recency_score = 0.0`. **ESTABLISHED.**

`src/dynasty_genius/league_opportunity_map.py:185` — a bare literal. No input, no data source, no
branch. It is then **summed into the headline `partner_score`** (`:189-195`) and **serialized into
`score_components`** (`:206`) beside three genuinely computed components (complementarity from
positional z-scores, divergence density from counted rows, posture alignment from labels).

**A consumer reading `score_components` cannot distinguish this constant from a measured zero.**

**Its root is M-1**: the component requires transaction history, which is never ingested. It is not
mis-weighted or badly designed — it is **uncomputable from anything in the system**, so **it cannot
be fixed at layer 5.**

## C-2. Coverage bound on this axis — stated so the single hit is not mistaken for completeness

A literal-assignment sweep over `src/` and `app/` for published score/rate/ratio/index/weight/
density/confidence fields returned **exactly one hit** (C-1). **That is one pattern, not a proof.**
It does not see: module-level constants referenced elsewhere; constant values inside dict/tuple
literals; fields whose name matches no keyword in the pattern; or values that are computed but from a
frozen or stale upstream. **This axis is PARTIALLY ASSESSED.**

---

# 7. THE DECLARED REGISTRY vs REALITY — a first-class finding either way

`src/dynasty_genius/sources/source_registry.py` declares **19 sources**. Three are live (§2.1).

**The cheap headline — "19 declared, 3 live" — is rhetorically effective and wrong, and I am
recording the rejection as a judgement rather than an omission.** The registry *does* encode status
in part: four sources carry the role `prohibited_current_phase`, and KTC carries an explicit ToS
prohibition. It is not a fantasy document.

## R-1. The registry has no `status` or `integrated` field, so **a reader cannot distinguish aspirational from live.** **ESTABLISHED.**

`SourceDefinition`'s complete field set is: `name · roles · allowed_fields · prohibited_fields ·
provenance_required · cache_policy · freshness_hours · failure_behavior · test_gate · notes`.

**There is no field expressing whether a source is actually wired up.** Live sources and intended
ones are structurally indistinguishable. This is the "what we believe we ingest vs what we do"
disagreement, and it is a **structural** property of the schema — not an accusation that any
individual entry is wrong.

**The merge added a second and worse direction, which my method alone could not see.** The registry
is not only over-inclusive — **it is also incomplete.** Established, actively-feeding sources that
appear **nowhere** in it:

- the **DynastyProcess / FantasyPros ECR** git-history archive (2,185 rows);
- the **first-party / manual identity and league inputs** — league context, alias bridge, prospect
  registry, prospect→NFL bridge, the frozen 2025 bundle, `ff_playerids` pins;
- the **Sleeper CDN** asset mirror;
- **general `nflreadpy`** loads beyond the two QB-specific registry entries.

It also retains the name **`nfl_data_py`** after the runtime client migrated to **`nflreadpy`** — a
deliberate legacy alias, but one that means the registry's own source name no longer matches the
library that runs.

**So the registry fails in both directions at once:** it lists sources that never run, and omits
sources that do. **Reading it to learn what this product ingests will mislead in both directions**,
and no field in the schema lets a reader tell which entries are which.

## R-2. `freshness_hours` does not define its own semantics, so it **cannot anchor a staleness judgement in either direction.** **ESTABLISHED. Resolution is David's, not mine.**

Six of 19 carry a declared cadence: `sleeper` **1h** · `fantasycalc` **24h** · `mfl_rookie_adp`
**24h** · `nfl_data_py` **168h** · `nflreadpy_qb_context` **168h** · `cfbd` **720h**.

Two observations, stated as facts and **deliberately left unresolved**:

- **`sleeper` declares 1 hour; the scheduled capture runs once every 24 hours.**
- **`mfl_rookie_adp` declares 24 hours and is not reachable from any scheduled job.** `cfbd` declares
  720 hours, same.

**I am not calling either a violation.** The field's entire documentation is `# None = static /
manual`, which leaves it ambiguous between a **cache TTL** and an **ingestion cadence** — and those
two readings imply opposite verdicts on the Sleeper figure. **The ambiguity is the finding: the one
field in the codebase that could anchor a staleness judgement does not say what it means.** David's
own axis requires a declared cadence before "stale" is meaningful; this field cannot yet serve as
one. **Resolving which meaning was intended is his call, not a lane's.**

---

# 8. FOR DAVID — is the foundation sound enough to build on?

**Answered per source, in his terms. Implied work is named and NOT authorised.**

## Sound, and better than expected

- **The daily pipeline runs and its outputs are fresh today.** Three sources ingest, six jobs produce,
  and everything the live path writes is stamped within hours.
- **Point-in-time capture is accumulating properly** — 1.1 GB across two stores, capture-and-append
  rather than overwrite. This is the compounding asset working as designed.
- **The backup is real.** Not asserted from a green marker: 267 objects pulled back out and
  byte-verified today.

## Not sound, in order of how much they constrain what can be built

1. **Layer 5 has no substrate.** Manager behaviour — every trade, waiver and add — is never ingested.
   A scoring component already ships a constant `0.0` in its place, published as though measured.
   **Nothing built on league behaviour can work until transactions are ingested.**
   *Implied work, not authorised: ingest `/league/{id}/transactions/{round}`.*
2. **The schedule is best-effort and slips silently.** Two multi-hour outages in thirteen days, plus
   catch-up storms, and every health surface reported green throughout.
   *Implied work, not authorised: cross-day lateness detection.*
3. **Already-ingested data is not reaching the surface.** 373 of 501 modeled players have their draft
   pick and round on disk and are served blank. A layer-2 join, not a missing source.
   *Implied work, not authorised: join the rookie table into the active feature dict — **but whether
   these fields are wanted on the active surface at all is a product question that is David's**.*
4. **The source registry cannot tell you what is real.** No status field; a cadence field with
   undefined meaning. **Anyone reading it to learn what the product ingests will be misled** — not by
   a false entry, but by a schema that cannot express the difference.
   *Implied work, not authorised: add an integration-status field; define `freshness_hours`.*
5. **A generation of `_latest` artifacts stopped advancing 2–5 weeks ago**, and whether any live
   surface still reads them is unestablished.
   *Implied work, not authorised: trace their consumers.*
6. **Governance checks over the gold layer have produced no observed result since 2026-07-24**, and
   the Databricks layer is **entirely unassessed** in this census because assessing it costs
   credentialed spend that was deliberately not taken.

## The honest bottom line

**Layers 1 and 2 are sound enough to keep building the things already built on them** — the market
lane, the model lane, and the daily surfaces all rest on sources that genuinely ingest and stores
that genuinely accumulate.

**They are not sound enough for the layer-5 advantage David has named as his edge**, and that is not
a tuning problem: the data has never been collected. **That is the single largest gap this census
found, and it is the one where "we haven't fortified layers 1 and 2" is literally true.**

**Status of this census: COMPLETE, with its limits named.** Both independent enumerations are done,
the diff has run (§1.5), the numeric divergence is resolved, and the merged source list is §2.1b.

**What "complete" does and does not mean here.** It means: two lanes enumerated by different methods,
the results were diffed rather than reviewed, five coverage holes in my method were found and
absorbed, and every remaining gap is named rather than absent. It does **not** mean the enumeration is
provably exhaustive — the diff found holes in one method and could have found more in both, and the
07-06 transactions probe proves that untracked activity leaves no repository trace at all.

**Deliberately NOT assessed, and requiring David's word:** the Databricks Bronze/Silver/Gold estate.
It is enumerated in §2.1b and its contents, grains, completeness and current existence are unknown.
No credentialed spend was taken.

**Not designed, per David's instruction that the census finishes before any work is shaped:** nothing
in this document opens a spec, a schema change, an ingestion, or a repair. Every "implied work" line
above is exactly that — implied, and stopped.
