# Codex lane view — next-session Layer 1/2 ordering

**Recorded:** 2026-08-03 10:13 EDT

**Scope:** planning only; no source, data, consumer, model, or promotion mutation

**Evidence basis:** current tracked code, untracked NGS files, SQLite tables/counts, last-good
export manifests, source-registry contract, and repository-wide Python caller searches. No claim
below uses `AGENT_SYNC.md` as evidence.

## 1. NGS disposition: do not land the three files

The three untracked paths are a superseded second adapter/store, not a clean feature body:

- `scripts/run_nfl_nextgen_capture.py`
- `src/dynasty_genius/capture/nfl_nextgen_capture.py`
- `tests/contract/test_nfl_nextgen_capture.py`

The tracked source registry already names `src/dynasty_genius/nflverse_usage.py` and
`app/data/nflverse_usage.db` as the **canonical** NGS adapter/store and records the second Parquet
route as withheld under the one-adapter-per-source rule. The canonical path already holds exactly
the same three NGS row counts as the duplicate snapshot — passing 5,933, receiving 14,731, rushing
6,059 across 2016–2025 — plus governed identity, snap counts, injuries, raw-before-parse snapshots,
projection-aware idempotence, typed exports, era replay, and a last-good reader.

This is stronger than “commit three files.” The untracked adapter treats every nonblank GSIS token
as resolved rather than checking the governed identity universe, creates a second store under
`app/data/sources/nfl_nextgen_stats/`, and lacks the canonical store/export/era contracts.

**Recommended next-session action:** audit for unique behavior, prove the canonical path is a
strict replacement, then remove the three untracked code/test files. Do not delete the duplicate
gitignored data tree in the same action; first compare and label it superseded, then obtain an
explicit data-retention disposition.

**Gate:**

1. One tracked source-registry adapter and one production store remain.
2. NGS family/season/row coverage reconciles: 5,933 / 14,731 / 6,059, 2016–2025.
3. The canonical last-good export is hash-verified and its NGS identity outcomes are measured.
4. `scripts/run_feature_refresh.py` and `scripts/assemble_engine_b_dataset.py` continue to read the
   canonical local export; no production Python caller references the withdrawn adapter.
5. Canonical NGS, registry, feature-refresh, and full-suite contracts pass after removal.

This is a **disposition/CLEAR cycle**, not a new RED/GREEN implementation.

## 2. Genuinely open Layer 1/2 items, measured now

### Layer 1

- **Canonical inventory reconciliation is open.** `docs/data-inventory.md` still says NGS lands in
  the withdrawn standalone store and has no consumer, and still lists injuries as unwired. Current
  disk/code state is the opposite: `nflverse_usage.db` has 34,812 injury rows; the tracked export
  contains all five streams; and two production scripts call `load_nextgen_from_export`.
- **nflverse contracts are not ingested.** Repository-wide Python search found zero callers of
  `nflreadpy.load_contracts`; the usage registry has no contracts StreamSpec/table.
- **nflverse depth charts are not ingested.** The same is true for `load_depth_charts`.
- **Four other named free nflreadpy families remain unwired:** FF opportunity, rankings, PFR
  advanced stats, and FTN charting. They are real open inventory rows, but not all belong in one
  session.
- **FantasyPros is historical-only and Footballguys has no feed.** Those are open against David's
  paid-source target, but implementation is blocked on what each subscription actually permits
  David to export or access.

### Layer 2

- PlayerProfiler's governed tables have no production consumer outside the ingestion modules.
- Most organized PFF families have no curated consumer; the receiving-summary path is the notable
  existing exception.
- The fresh isolated CFBD candidate is not the active Engine A input.
- Injuries have no consumer.
- NGS is **not** accurately described as consumerless: feature refresh and Engine B dataset
  assembly both read its last-good export. That is data plumbing, not evidence of predictive value
  or authorization for feature/model promotion.

## 3. Recommended ordering

1. **NGS disposition + inventory truth repair.** Remove the duplicate code path after the gate
   above; correct the NGS/injuries rows and the stale “nothing downstream reads it” module prose.
2. **Contracts ingestion, end to end.** Live shape/fingerprint preflight, framing/RED, canonical
   identity and grain, raw capture, durable store, typed last-good export, schema-era fixtures,
   live capture, independent CLEAR.
3. **Depth-chart ingestion, end to end**, with the same sequence and a separately measured
   contract. Do not batch both sources behind one generic schema.
4. **Stop and remeasure Layer 1.** Present David the remaining free/paid inventory and the exact
   FantasyPros/Footballguys access questions. Only then choose the next source or open Layer 2.

Agreement with Claude: the ingestion substrate is ahead of curation, and NGS should be the first
small closeout. Disagreement: “ingestion is ahead” does **not** imply Layer 2 should open next.
David's latest sequence was injuries, then return to finishing Layer 1 inventory ingestion. The
measured contracts/depth-chart gaps and stale canonical inventory mean that instruction is not yet
satisfied.

## 4. Explicit deferrals for the next session

- CFBD promotion, active-training CSV mutation, bakeoff, model work, or consumer promotion.
- QB-1 execution; QB rushing remains **a hypothesis under test**, not a finding.
- Broad PlayerProfiler/PFF feature curation or “try everything” exploration.
- Any broader mutation campaign beyond the completed 12-mutant pilot.
- Schedulers for new streams before their manual capture/replay contracts are proven.
- FF opportunity, rankings, PFR advanced stats, FTN charting, FantasyPros implementation, and
  Footballguys implementation unless contracts + depth charts finish and David explicitly selects
  one from the remeasured inventory.
- Deletion of the duplicate gitignored NGS data tree without a separate retention decision.

The intended next-session finish line is deliberately short: withdrawn NGS path resolved,
inventory truthful, contracts production-grade, depth charts production-grade, then stop.

## Amendment after Claude's independent verification

Claude independently reproduced the NGS counts, consumer callers, six unwired loaders, and stale
inventory claims, then accepted the ordering. His amendment is accepted: every newly landed stream
must carry an explicit consumer disposition so “unwired” is a recorded choice, not an accidental
accumulation.

The disposition is a closed, machine-readable planning field with one of these states:

- `existing_consumer`: name the exact reader path and permitted use.
- `substrate_only`: name the decision owner, why no consumer is being built now, and the separate
  validation/authorization gate required before use.
- `blocked_for_use`: name the semantic, identity, coverage, licensing, or freshness defect that
  makes consumption unsafe.

This is not a requirement to manufacture a consumer in the ingestion session. Contracts and depth
charts may legitimately land as `substrate_only`; their football interpretations remain candidate
hypotheses until a later Layer 2 contract and validation establish what may be derived.
