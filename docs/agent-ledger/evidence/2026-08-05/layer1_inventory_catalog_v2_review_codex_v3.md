# Layer 1 Data Inventory Catalog v2 — Codex Review v3

**Review target:** `docs/layer-1-data-inventory-catalog.md`

**Target SHA-256:** `44bf34a7585631160d6e80131c8388fcb87b85551cf13d01d239164e47ed5df9`

**Reviewed:** 2026-08-05 22:18 EDT

**Layer:** Layer 1 — ingestion inventory
**Disposition:** **NOT CLEAR for phase B.** Claude's F1–F7 dispositions are accepted as corrective
direction, but the target explicitly remains incomplete and four cells/statements still contradict
its own rules or measured repo state.

No Layer 2 research, build, capture, scheduler, consumer, model use, commit, or push is opened by
this review. H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result.

## Checks performed

1. Recomputed the target hash and read all 269 lines.
2. Loaded `SOURCE_REGISTRY`: exactly 20 definitions, matching the names at catalog lines 74–77.
3. Loaded `build_streams()`: exactly 13 bound specs — twelve seasonal and `contracts` snapshot.
4. Queried every canonical SQLite stream table plus both capture ledgers.
5. Read `app/data/nflverse_usage/export/nflverse_usage.ready.json`: twelve stream files, 1,491,691
   observation rows, and a separate unresolved-identity file.
6. Recomputed the PlayerProfiler, FantasyCalc-forward, and Sleeper-transaction decompositions by
   physical table.
7. Inspected `scripts/run_feature_refresh.py`, `load_nextgen_from_export`, and production callers.
8. Parsed all eight `ops/launchd/*.plist` schedules and read `app/config/report_freshness.json`.
9. Read Gemini's live transcript, not only its ledger summary. Ran both cockpit hygiene tripwires;
   both passed. Re-read the live backup marker.

## Accepted corrections

- **The 101-row delta is fully resolved.** Twelve source tables sum to **1,491,691 `obs`** and
  `nflverse_capture` contains **101 `cap`** rows. The physical total is 1,491,792; 1,491,792 is not
  an observation total.
- PFR is correctly split: pass 5,424; rush 18,461; receiving 35,724; defense 62,345.
- The other decompositions reproduce exactly:
  - PlayerProfiler: 1,520,009 `obs` + 3,290 `idn` + 63 `cap`.
  - FantasyCalc forward: 20,043 `obs` + 20,043 `alt`; the alternate rows are not additive.
  - Sleeper transactions: 932 transactions + 1,692 movements at a different observation grain +
    4 capture rows.
- Feature Refresh does not refresh the canonical store. It reads only the three NGS exports and
  independently downloads player stats, rosters, snap counts, play-by-play, and participation.
  No LaunchAgent invokes the canonical usage-capture runner.
- Gemini's operational contribution is correctly labelled telemetry, not a catalog pass. The live
  backup marker still reports run `20260805T141503Z`, `status=failed`,
  `sha256_verified=false`, finished `2026-08-05T16:29:23.476095Z`, with the recorded
  `upload_failed:<path>` failure. The timeout explanation is withdrawn. The separate 05:13:15Z
  projected staleness time remains unverified because it mixes clock operands.

## Findings

### V2-F1 — MEDIUM: the current source-row count is stale inside the rebuilt document

Catalog line 55 says **9 rows enumerated**, but Table A contains **7 rows** (A1–A7). The line may
describe v1's pre-merge count, but it is written as current progress. This is another instance of
the document's own state-recheck failure. Change it to seven current rows or label it explicitly as
the superseded v1 count.

### V2-F2 — HIGH: Table B does not implement its declared multi-valued state contract

R7 requires separate `bound`, `captured`, `exported`, `consumed`, and `decision_supported` state.
Table B omits **`exported` and `decision_supported`**, and places `blocked_for_use` in B14's
`consumed` cell. That makes disposition, consumer existence, and decision-grade status one field
again. Add all five columns and keep landing disposition separate if it remains needed.

Positive evidence already exists for `exported`: the ready manifest contains all twelve
materialized canonical streams. `contracts` and `ff_rankings` are not exported.

### V2-F3 — HIGH: line 180 conflates bound configuration with materialized store state

The repo has **13 bound StreamSpecs**, but the SQLite store has **12 source tables**; `contracts`
and `nflverse_snapshot_capture` are absent. Therefore “the canonical ingestion store — 13 streams”
is false at the store grain. State the three facts separately:

- 13 bound specs;
- 12 materialized/exported stream tables totaling 1,491,691 `obs`;
- no scheduled canonical capture for any bound spec.

The following nine-consumerless-materialized-stream statement is supportable only after B4 is
closed as described below.

### V2-F4 — MEDIUM: §6 promotes B4's unresolved consumer cell to an established gap

B4 says the canonical `snap_counts` consumer is `UNVERIFIED`, while §6 says nine stored nflverse
streams have no consumer. Independent caller inspection now resolves B4: the canonical
`player_snap_count` export has **no production consumer**. `run_feature_refresh.py` and the other
named scripts call `nflreadpy.load_snap_counts` directly; that is a separate provider-read stream,
not a consumer of the canonical export. Update B4 to `none`, cite the caller/export probe, and name
the nine materialized consumerless streams individually before retaining the §6 count.

## Completion blockers already disclosed by v2

These are not new findings, but they remain hard blockers on phase B and on answering David's
source-gap question:

- Table A needs rows for all 20 registry definitions plus non-registry sources.
- Table B needs non-nflverse streams and direct provider-read streams.
- Every job row needs its plist/log/marker evidence path and observation timestamp.
- Stream cadence must remain separate from job-fire and freshness-policy cadence.
- Candidate external sources cannot be assessed until the current universe is enumerated.

## Reviewer conclusion

The rebuilt catalog is materially safer than v1: its observation counts, grain decompositions,
Feature Refresh semantics, and Gemini alarm boundary now withstand direct probes. It is still an
**inventory increment**, not a phase-A completion artifact. Close V2-F1–F4 and the explicitly owed
enumeration/evidence work, then route a fresh complete A–C target. Phase B remains closed.
