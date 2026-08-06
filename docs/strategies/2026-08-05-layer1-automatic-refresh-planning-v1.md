# Layer 1 Automatic Data Refresh Planning — v4

**Status:** planning increment, not execution authority

**Layer:** Layer 1 ingestion. This plan does not open Layer 2.

**Catalog dependency:** the final plan cannot claim “all possible streams” until sections A–C of
`docs/layer-1-data-inventory-catalog.md` are complete and independently clear. Planning starts now;
implementation does not.

## 1. Objective

Create production-grade, season-aware automatic refreshes for every Layer 1 stream that can be
refreshed legally, technically, and within a David-approved cost ceiling. Every stream must end in
exactly one automation class:

1. `automatic_active_verified` — governed job exists and its operational health is evidenced;
2. `automatic_active_health_unverified` — governed job fires, but freshness/health is not yet proven;
3. `automatic_candidate` — technically possible, but no governed job exists;
4. `manual_only` — current access path requires a human export or upload;
5. `blocked` — a named identity, storage, source, use, or authority blocker prevents scheduling;
6. `prohibited` — policy, terms, cost, or governance bars the source in the current phase;
7. `static_pinned` — immutable validation/history input whose correct cadence is no refresh.

“Not scheduled” is not a cadence. “Daily job” is not proof of daily source change. “Possible” does
not imply authorized.

## 2. Required row contract

Each source-stream row in the final schedule carries:

| Field | Meaning |
| :-- | :-- |
| source and stream IDs | provider family and exact dataset/loader grain |
| automation class | one of the seven classes above |
| source publish cadence | measured upstream change rhythm, or `UNVERIFIED` |
| stream refresh cadence | season-aware capture target |
| job fire cadence | how often the scheduler checks/runs |
| freshness policy | when the artifact is stale; separate from job fire |
| season window | in-season, offseason, event-triggered, or year-round |
| dependency edges | upstream capture and downstream consumers |
| raw/normalized/store paths | physical lineage and market/model separation |
| identity gate | required bridge and unresolved-row policy |
| last-good behavior | unchanged, partial, failed, and recovery semantics |
| marker/log paths | timestamped operational truth surfaces |
| operational health basis | latest status, freshness result, and observation window; never inferred from a fire |
| cost/access basis | free, paid-per-call, subscription, manual export, prohibited |
| approved cost ceiling | numeric/run-rate budget or `UNVERIFIED`; “economical” is not a verdict |
| owner and authority gate | who decides and what word is still required |

## 3. Provisional classification from the current incomplete inventory

This table is deliberately provisional. Rows not yet enumerated in the catalog remain open work.

| Source/stream group | Current state | Planning class | Constraint before scheduling |
| :-- | :-- | :-- | :-- |
| Sleeper league capture | daily 09:20 job; registered freshness, 21 consecutive successful runs, empty error log, current status/ready markers, loaded job last exit 0 | `automatic_active_verified` | exact endpoint raw replay and request-time Roster Auditor reconciliation remain separate quality/route gaps |
| FantasyCalc forward capture | daily 09:00 job; no registered freshness row | `automatic_active_health_unverified` | add its missing freshness-policy row and preserve physical market separation |
| nflverse canonical store: 13 bound specs | manual capture only; 12 materialized | `automatic_candidate` | complete per-stream cadence, source-publish, and dependency rows; `contracts` has never run |
| Feature Refresh direct read: snap counts | canonical B4 is already materialized/exported (253,106 rows), but the daily job bypasses it with a second live read | `automatic_candidate` | schedule the canonical capture, add a ready-export loader and durable candidate-equivalence control, then remove the duplicate live route |
| Feature Refresh direct reads: player stats, rosters, PBP, participation | current daily 09:15 live routes are active but health-unverified; no canonical capture streams | current `automatic_active_health_unverified`; desired Option A canonical routes are `automatic_candidate` | define exact-byte raw capture, normalized partitions, independent source vintages, atomic bundle, and backup treatment; migrate consumers rather than keep invisible provider reads |
| nflverse Combine | live input to an active training-file builder; upstream runs 12:00/17:00 UTC March 3–12 plus manual dispatch | `automatic_candidate`; proposed one conditional 20:00 UTC check March 3–13 | capture exact source bytes and parser/version provenance before the builder may consume a new vintage |
| nflverse schedules / Realized Outcome player stats | schedules update every five minutes in season; loaded weekly consumer runs Tuesday 10:00 local and currently no-ops before provider access because prediction snapshots are absent | `automatic_candidate`; proposed Tuesday 06:15 ET year-round conditional check | capture exact source/finality vintage and consume last-good before the first prediction-bearing run; no intraday local cadence without a named consumer |
| nflverse draft picks — forward route | upstream 05:00 UTC Wednesdays Sep–Feb, additionally daily Feb 1–15 and Apr 23–May 5 | `automatic_candidate`; proposed conditional 12:00 UTC checks on those days | exact transport/source bytes; frozen 2025 payload remains physically `static_pinned` |
| DynastyProcess `db_playerids` — forward route | upstream Friday 00:23 UTC plus manual dispatch; observed delivery lag | `automatic_candidate`; proposed Friday 08:15 ET blob check and one Saturday retry after Friday no-change/failure | exact CSV + upstream commit/blob provenance; frozen 2025 crosswalk remains physically `static_pinned` |
| Sleeper transactions/movements | manual store today | `automatic_candidate` | define incremental cursor/idempotence, league-history backfill, and status marker |
| Sleeper league-behavior raw history | one-time exact endpoint capture for 2023–2026; backup-covered; omitted from canonical catalog | `manual_only` pending a recurring-use decision | row endpoint-specific grains and provenance first; do not sum unlike endpoint payloads |
| CFBD | paid HTTP source; registered 720-hour freshness for historical data | `blocked` pending cost/run policy | David approves automated paid-call budget and season/event cadence |
| PlayerProfiler | current store was manually landed; shadow retrieval exists | `blocked` pending access/legal/reliability audit | prove a sanctioned stable acquisition path before calling it automatable |
| PFF, RotoViz, Campus2Canton | manual CSV/export paths in registry | `manual_only` | no automated API in the current contract |
| `nfl_data_py` / equivalent nflverse historical labels | registered 168-hour freshness, stream inventory incomplete | `automatic_candidate` | enumerate actual loaders/stores and avoid duplicating the canonical nflverse adapter |
| MFL rookie ADP | public API and separated destination exist, but the current undocumented adapter query returns veterans rather than a rookie-only cohort | `blocked` | correct/re-RED against the official `IS_KEEPER=R&IS_MOCK=0` contract and prove cohort semantics before first capture or scheduling; never enter Engine A/B |
| DynastyProcess pinned backtest files | immutable registered evidence | `static_pinned` | no refresh unless a separately versioned forward-history use is approved |
| `ff_rankings` | `blocked_for_use`, no RED | `blocked` | remains outside scheduling; current ruling permits no scheduler |
| KTC | scraping prohibited by registered source rule | `prohibited` | official/sanctioned API plus David's new ruling required |
| Dynasty Data Lab / DynastyNerds | paid or no clean API; deferred | `blocked` | explicit use, access path, cost, and destination before ingestion planning |
| Sportradar / Genius Sports / Stats Perform / Rolling Insights | enterprise cost/licensing, prohibited current phase | `prohibited` | David-only source/cost decision |
| QB validation source set | pinned study inputs | `static_pinned` unless the ratified study says otherwise | never silently refresh a pre-registered input manifest |

**Source-cadence companion:**
`docs/agent-ledger/evidence/2026-08-06/layer1_source_publish_cadence_codex_v1.md` is independently
CLEAR at SHA-256 `2d1fe261b8c88a75091ca48e0951348d64b26bee7696bc28a8abaaa8ff2387fe`.
Its clocks remain planning targets, not installed jobs. Its load-bearing finding is that the current
single five-frame loader lets postseason-only participation cap the entire season window; separate
capture clocks and a bundle manifest are therefore correctness requirements, not scheduling polish.

**Remaining-candidate cadence companion:**
`docs/agent-ledger/evidence/2026-08-06/layer1_remaining_candidate_cadence_codex_v1.md`, SHA-256
`af31195ccc6cd99ff8f6fea2db2e3498cf94eb2b7aab7908d5be8582de6b7019`.
It is the evidence source for B20/B21/B22/B23's upstream rhythms and proposed checks, and for R9's live
endpoint-contract block. Workflow fires and local checks create no observation when bytes are
unchanged.

## 4. Target dependency shape

```text
source availability/change
        |
        v
raw capture + provenance + content hash
        |
        v
schema/identity/reconciliation gate
        |
        v
atomic last-good store/export + status marker
        |
        +--------------------+
        |                    |
        v                    v
curation/feature refresh   operational freshness monitor
        |
        v
downstream model/context jobs only when separately authorized
```

The current 09:15 Feature Refresh does not occupy the raw-capture box. It consumes three NGS
exports and directly downloads five other datasets. The final plan must eliminate that ambiguity
before adding more clocks.

## 5. Scheduling principles

1. **Schedule by source and meaningful change rhythm, not one universal daily job.** One job may
   cover several streams only when they share source, cadence, failure boundary, and provenance.
2. **Season-aware cadence is mandatory.** Injuries/depth/league state may justify a faster
   in-season check than historical aggregates. Offseason and dormant windows are explicit.
3. **Capture precedes consumers.** A downstream job reads only a successful last-good artifact,
   never an ungoverned live provider call hidden inside derivation.
4. **No fake history.** An unchanged pull records a checked/no-change outcome; it does not create a
   new source observation unless the stream contract explicitly defines observation-time snapshots.
5. **Fail closed, preserve last good.** Schema drift, partial source response, identity failure,
   and export failure surface in a marker and never replace the last-good artifact.
6. **Each job owns a lock and a terminal marker.** Marker absence, failure, or policy-defined
   staleness is visible. Logs are evidence, not the status API.
7. **Retries are bounded and source-safe.** Backoff, rate limits, paid-call ceilings, and retry
   idempotence are defined before scheduling.
8. **Market and validation data stay isolated.** Automation never relaxes the market-overlay wall
   or changes a pinned study manifest.
9. **Manual fallback is part of the contract.** `manual_only` is a supported operating state, not a
   hidden failure to automate.
10. **Backup coverage follows new irreplaceable stores.** Any new capture store must enter the
    governed backup manifest in the same implementation change.
11. **Backup health is an enablement precondition.** No new persistent automatic capture is enabled
    while `app/data/ops/backup_status_latest.json` reports failure. If a proposed cache is genuinely
    regenerable and outside the protected set, the plan states that basis explicitly rather than
    silently bypassing this precondition.
12. **The manifest test has a known enforcement gap.** The current anti-rot test mechanically scans
    present top-level databases and registry paths, not arbitrary raw directories, CSV, pickle, or
    export artifacts. Until a RED extends it, reviewers must verify those paths manually. P4 must
    either extend the scan or record reviewer evidence for every new governed artifact.
13. **Pinned inputs are physically immutable to automation.** Any forward DynastyProcess or
    validation capture writes to a separate path and job identity that cannot overwrite a pinned
    manifest or registered input. One provider may have streams in different automation classes;
    nobody schedules “the source” as a unit.

## 6. Proposed planning sequence

### P0 — Finish the inventory

- Complete all source and stream rows, including direct provider reads, fixtures, deferred and
  prohibited sources.
- Attach source cadence, job cadence, freshness policy, evidence paths, and timestamps separately.
- Draw exact producer/store/export/consumer edges.
- Define each stream's season window in a versioned schedule/config row, with an owner. Do not
  borrow the constitution's estimate-responsiveness seasons as an ingestion calendar.
- For every paid source, carry an explicit approved per-run/month ceiling or `UNVERIFIED`.
- Reconcile the existing Sleeper raw league-history capture, Combine, schedules, parallel
  Sleeper/FantasyCalc routes, and every additional consumer edge before declaring the route universe
  complete.
- Carry the point-in-time ceiling explicitly: current nflverse raw history begins 2026-07-31;
  historical-season rows are not historical as-of vintages.

### P1 — Ratify the automation classification

- Codex verifies technical/source evidence row by row.
- Gemini verifies job, marker, log, fire, and freshness facts only.
- Claude dispositions every challenge.
- David rules on paid-call budgets, access methods, prohibited-source exceptions, and priority.

### P2 — Design the canonical nflverse refresh program

- Group only streams with proven shared cadence/failure boundaries.
- Route all five Feature Refresh inputs through canonical capture before derivation. `snap_counts`
  must reuse existing B4 and retire its duplicate live read; the other four need new governed
  capture contracts. The three-lane pressure test and David's disclosed direction select this
  Option A architecture for planning; implementation and enablement remain separately gated.
  Letting the live reads remain a parallel production ingestion surface would
  contradict `01` §Source Adapter Rules and the one-trustworthy-path standing goal; that alternative
  requires an explicit governance amendment, not an ordinary architecture preference.
- Define season windows, dependency ordering, locks, markers, and last-good publication.
- Preserve the contracts snapshot semantics and weekly cadence already ruled; scheduling remains a
  separate authority gate.
- Treat the first scheduled contracts capture as its product-store landing: before enablement, run
  one export covering all twelve prior streams plus contracts, reconcile prior published files and
  the NGS consumers, obtain the separate landing/scheduling word, and pass independent review.

### P3 — Extend to context and overlay sources

- Automate Sleeper transactions after incremental-history/idempotence design.
- Close FantasyCalc freshness monitoring.
- Keep MFL ADP blocked until its endpoint contract is corrected and independently proves a
  rookie-only cohort; a future authorized repair must update the adapter, its stale
  `SOURCE_REGISTRY` declaration/notes, and RED controls together. Only then consider capture in the
  physically separated overlay store.
- Resolve paid/manual sources individually; do not manufacture unsupported scrapers.

### P4 — Operational acceptance before enablement

For every job: preflight, dry-run/candidate mode, success/no-change/failure/recovery controls,
staleness positive control, lock contention, last-good preservation, backup-manifest coverage, and
independent review. For raw directories/CSV/pickle/export artifacts, extend the anti-rot test or
attach explicit reviewer-enforced manifest evidence. Require a non-failed live backup marker before
enabling new persistent capture. Enabling a LaunchAgent is a separate David-authorized action after
these gates.

## 7. Decisions that remain David's

1. Which `automatic_candidate` streams receive build priority.
2. Numeric paid-call budgets and acceptable refresh frequency for CFBD or any paid source.
3. Whether any currently prohibited enterprise source is reopened.
4. The implementation priority and enablement batch for Option A. The pressure test is complete:
   Claude, Codex, and Gemini recommend canonical Layer 1 capture, and David stated that Option A is
   better. Remaining design choices include per-stream retention ceilings, bundle publication,
   backup treatment, and the order in which consumer routes migrate. Retaining a parallel surface
   is not a peer option under current governance; it requires an explicit `01` amendment that David
   is told he is making.
5. The final enablement word for each scheduled job or approved batch.
6. The exact in-season/offseason/event boundaries for each cadence family, after source-publish
   rhythms are measured.

## 8. Explicit non-actions

No scheduler, LaunchAgent, capture, store, consumer, model input, market overlay, commit, or push is
created or authorized by this plan.

**Backup recovery is complete.** David clarified *“i meant RUN IT.”* Authorized run
`20260806T024853Z` completed with 508 files, 2,203,676,656 bytes, verified hashes, and zero failures.
This clears the failed-marker precondition only; it does not prove the prior failure mechanism,
extend manifest coverage, set retention ceilings, or authorize any scheduler, capture, or product
action.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result.

## 9. Disposition of Claude challenge C1–C7

| Finding | Disposition |
| :-- | :-- |
| C1 backup authority conflict | **Accepted; resolved by David.** “RUN IT” authorizes the next-session manual backup/recovery. |
| C2 parallel direct-read branch requires governance amendment | **Accepted.** Canonical capture is the compliant default; the alternative is labelled an explicit `01` amendment. |
| C3 active jobs were called healthy without evidence | **Accepted.** Automation existence and health are split; Sleeper/FantasyCalc are health-unverified. |
| C4 failing backup constrains new capture | **Accepted.** Non-failed backup marker added as a persistent-capture enablement precondition. |
| C5 backup anti-rot enforcement gap | **Accepted.** Reviewer-enforced gap named; scan extension or explicit evidence required in P4. |
| C6 pinned inputs need physical immunity | **Accepted.** Separate paths/job identities required; one source may have streams in different classes. |
| C7 scheduled contracts capture is a landing | **Accepted.** Twelve-prior-stream-plus-contracts export reconciliation and separate authority are explicit. |

Both minor findings are accepted: paid-source “economics” requires a numeric ceiling, and every
season window needs a versioned boundary/owner rather than borrowing an unrelated estimate rule.
