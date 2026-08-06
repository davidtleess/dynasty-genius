# Layer 1 canonical catalog review — Codex v1

**Date:** 2026-08-06 (America/New_York)  
**Layer:** Layer 1 data inventory  
**Verdict:** **NOT CLEAR**  
**Scope:** independent read-only verification. This artifact authorizes no capture, adapter,
scheduler, store, consumer migration, paid call, commit, push, or Layer 2 work.

The existing SQLite counts largely reproduce, but the canonical source/stream inventory remains
incomplete and internally inconsistent. The catalog should not check off A, B, C, H, or I yet.

## CV1 — HIGH: existing Sleeper raw league history is omitted

`app/data/research/league_behavior/raw/2026-07-19/` contains **173 files**: 172 exact endpoint
envelopes plus `fetch_log.json`, covering 2023–2026. The fetch log records 176 calls and no failed
calls. `app/config/backup_manifest.json` covers the directory.

R13, A7, and Table B-N must add a distinct manual one-time, exact-raw, replayable stream without
summing unlike endpoint grains. It is not the daily normalized N18 bundle or the transaction store.

## CV2 — HIGH: Sleeper and FantasyCalc have additional acquisition routes

- Sleeper also has a request-time live route through `app/services/roster_auditor.py:408-446`.
- FantasyCalc has the daily forward store **and** `app/cache/fantasycalc/market_values.json` with a
  live fallback in `src/dynasty_genius/adapters/fantasycalc_adapter.py:89-144`, consumed by the trade
  API and market-overlay service.

R13's “TWO routes” and R8's forward-store-only description are incomplete. These are parallel-route
reconciliation defects, not new providers.

## CV3 — HIGH: B15–B19 consumer edges are incomplete

`scripts/assemble_engine_b_dataset.py:218-223` directly loads all five datasets again. B18 also
feeds Roster Auditor through the QB-context adapter. Keep one stream per upstream dataset, but name
every consumer edge; do not create duplicate stream rows for callers.

## CV4 — HIGH: Combine and schedules streams are absent

- NFL Combine is live input to the active training-file builder at
  `scripts/build_w2_features.py:520-524,565-647`, with no replayable capture found.
- Schedules are a future-live input to the loaded weekly Realized Outcome job at
  `scripts/run_realized_outcome_scoring.py:337-383`; that job also adds another player-stats
  consumer. Current logs show four `no_predictions_for_target` no-ops, so those provider reads have
  not flowed yet.

Row Combine as active-builder/uncaptured and schedules as future-live/uncaptured.

## CV5 — HIGH: R19 overstates its source-registry declaration

R19 is declared specifically as `nfl_nextgen_stats`; its registry notes cover the three NGS
families. The canonical adapter binds ten additional families in
`src/dynasty_genius/nflverse_usage.py:1189-1198`. “Shared adapter/store” is not the same as a
matching machine source declaration. R19 must not be described as declaring B1–B13.

## CV6 — HIGH: CFBD rows use the wrong grain and consumer claim

N16's 874 rows are a **multi-source curated training artifact**, not 874 CFBD source observations.
The manifest names the active training CSV as an input, and CFBD feature coverage is concentrated
in QB fields. The current board says no model consumes the corrected values. Record callable
builders/evaluators rather than the broad consumer label “Engine A.” N17's 1,202 is a raw-payload
count, not a source-observation count.

## CV7 — MED: PFF materialization and file-count prose are incomplete

The 149 raw payload count and 134,392 source-row sum reproduce, but `yprr_college` is populated on
**0 of 874** active rows despite the builder projection. This is a materialization/curation gap.
Disk holds 149 raw payload CSVs and 153 CSVs total; 307 file-map records are not additional raw
files. The current “459 raw CSVs” prose is false.

## CV8 — MED: MFL destination is already designed

R9's “overlay destination undesigned” statement is false. The adapter, a neutral
`decision_supported=False` divergence artifact, and the separated `app/data/valuation` destination
exist. Correct physical state: adapter and destination built; zero cache, output artifact, or
scheduler currently present.

## CV9 — MED: N18 endpoint and normalization ceilings are incomplete

A normal N18 run makes **nine** upstream requests, not eight. The normalized player projection also
drops `injury_status`, `injury_body_part`, `practice_participation`, and `injury_start_date`, keeping
only generic source `status`. This ceiling belongs in R13/N18 because it governs whether a new injury
provider is actually needed.

## CV10 — MED: captured history is not point-in-time history

The 1,019 nflverse raw files have capture dates only on 2026-07-31, 08-02, 08-03, and 08-05.
Historical-season rows are retrospective coverage, not historical as-of vintages. Preserve
`captured = true`, but record this point-in-time ceiling across B1–B12.

## CV11 — MED: canonical prose contradicts itself

- §3.1 says Table B-N has mixed independently verified cells, then says no row is verified.
- §4.1 says job evidence paths are durable, then says they remain to be attached.
- §4.2 says the five direct reads are not in the catalog even though B15–B19 are present.

These must be reconciled at the canonical sentence, not explained in another appendix.

## CV12 — HIGH consequence: §6 has not incorporated the completed source-gap pass

§6 omits the raw league-history capture, Combine/schedules, the parallel Sleeper/FantasyCalc routes,
the PFF materialization gap, MFL's built destination, and the point-in-time ceiling. Its “candidate
new sources NOT ENUMERATED” claim is stale.

The honest current answer to David is: **substantial existing-source capture and reconciliation work
is proven; no unconditional new external provider is yet proven necessary.** Production RAS remains
conditional on its narrow governed use and legal acquisition terms. A replacement injury provider
is conditional on an in-season completeness test of the existing Sleeper fields.

## Reproduced and sound

- all 20 registry declaration fields;
- B1–B12 SQLite counts and the 1,491,691-row export subtotal;
- PlayerProfiler counts/grains and FantasyCalc database counts/date ranges;
- Sleeper transaction counts;
- CFBD raw payload count 1,202;
- PFF 149 raw payloads and 134,392 raw source-row sum;
- contracts is bound but uncaptured.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result.
