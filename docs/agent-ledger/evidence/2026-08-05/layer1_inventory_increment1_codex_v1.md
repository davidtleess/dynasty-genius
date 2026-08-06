# Layer 1 Data Inventory — Codex verification increment 1

Date: 2026-08-05
Layer: Layer 1 data foundation
Lane: Codex, independent adversarial verification and source-gap analysis
Status: first measured increment; no catalog row is globally cleared by this artifact

## Authority and boundary

David directed the team to inventory Layer 1 sources, ingestion streams, refresh frequencies,
catalog, Player 360, semantic layer and metrics, and schemas; keep the inventory diligently; identify
sources still needing ingestion; and finish a checked Layer 1 Data Inventory Catalog before Layer 2
consumption research opens.

This artifact starts the independent verification lane. It authorizes no push, ingestion, capture,
landing, scheduler, consumer, model/feature use, or Layer 2 design. H2 QB rushing remains a
registered hypothesis UNDER TEST with no result.

## Checkpoint 0 — post-commit divergence audit

Verdict: **CLEAR for the requested divergence checks.**

- Commit `2a427594e83705c8eabdf1dc696826a4e268275c` contains exactly two paths:
  `src/dynasty_genius/nflverse_usage.py` and
  `tests/contract/test_contracts_ingestion_red.py`.
- Their working/HEAD SHA-256 values are respectively
  `f2a62bad99b51618fe8f80c57e652d57092527de8e368bd027a4541921c9a957` and
  `62c3073050f00b4e6e1168a5f7d9f5f0a41397bea3b6083f3646454561ef89f0`, exactly the v16 CLEAR pins.
- Implementer evidence `contracts_v12_green_claude_v16.md` remains
  `4bd67eb4bb15d1c34a093413e99fd49e99139cd042022dc29a582e3dbd1e0179`, also exactly pinned.
- Commit `748b42bd69877b37394a01c13d8237f010ba6452` has parent `2a42759` and contains exactly the
  declared two modified state documents plus ten added evidence documents. It contains no source,
  test, fixture, app, script, config, store, or data path.
- `HEAD` was `748b42b`; `origin/main` was `9f8dd0d`; the branch was two commits ahead and unpushed.
- Commit 1 passes `git diff --check`. Commit 2 preserves CommonMark two-space hard-breaks in five
  Codex evidence headers, which `git diff --check` reports as trailing whitespace. This is disclosed
  as a state-document formatting observation, not an execution-surface or content-pin divergence.
- After Claude's clean-tree measurement, Gemini appended its first telemetry entry to
  `docs/agent-ledger/2026-08-05.md`. The current dirty ledger is therefore new inventory state, not
  divergence inside either audited commit.

## Increment 1 — establish the catalog's entity levels

### Measured baselines

1. Existing durable seed: `docs/data-inventory.md`, 247 lines, SHA-256
   `d9d59ffcc320be158c42e78fbbbf18962c6f5b3991f17d518286446c6a9acd01`; last committed in
   `5be8a53` on 2026-08-03. It contains an external-source table, a derived-store table, and prose
   gap notes.
2. Machine semantic registry: `src/dynasty_genius/sources/source_registry.py`, SHA-256
   `a840d6f72c3bbdbe36a69e2aca7bf9cbf05c7cdafc75353b78217a28be6eccd6`. Importing
   `SOURCE_REGISTRY` yields 20 definitions. This registry classifies roles, allowed/prohibited
   fields, cache policy, nominal freshness, failure behavior, and test gates; it is not a complete
   inventory of sources used on disk or ingestion streams emitted.
3. Canonical nflverse adapter at `2a42759`: `build_streams()` returns 13 loader-bound `StreamSpec`
   objects — `ngs_passing`, `ngs_rushing`, `ngs_receiving`, `snap_counts`, `injuries`, `pfr_pass`,
   `pfr_rush`, `pfr_rec`, `pfr_def`, `ff_opportunity`, `ftn_charting`, `depth_charts`, and
   `contracts`. Twelve are seasonal; `contracts` is snapshot-axis.

### INV-1 — source and ingestion stream must be separate catalog entities

**Finding:** the current prose inventory has one broad `nflverse via nflreadpy` source row while the
canonical adapter alone exposes 13 independently shaped streams. A single `ingested today?` cell
cannot represent loader availability, bound contract, raw capture, normalized storage, export,
consumer, freshness, and decision use without collapsing different states.

The old free-loader prose illustrates the ambiguity: it calls `contracts` unwired, while the present
repo has a loader-bound snapshot `StreamSpec`; nevertheless contracts has no capture/landing and zero
product-store rows. Both statements can sound true because `wired` was never decomposed.

**Required catalog rule:** `source_id` and `stream_id` are independent stable keys. One source may
have many streams; every Player 360 field and semantic metric must reference an exact `stream_id` and
schema field, not only a provider name.

### INV-2 — existing inventory requires cell-level remeasurement

**Finding:** the seed is internally stale. Its missing-sources section says CFBD's cache and PFF's
manual files are “about two months old,” while its own source rows record an isolated CFBD refresh on
2026-08-02 and PFF payloads on 2026-08-01. Document-level inheritance is therefore unsafe; each cell
needs evidence and a measurement timestamp.

No row in `docs/data-inventory.md` is treated as confirmed merely because the document is tracked.
Prior statements are discovery seeds until reproduced or explicitly marked attributed/unverified.

### Gemini operational intake — increment 1

Gemini accepted the telemetry lane and produced a first jobs/cadence/marker table. Codex then read
the actual transcript and reproduced the highest-risk marker facts:

- `app/data/ops/backup_status_latest.json` records run `20260805T141503Z`, started
  `2026-08-05T14:15:03.979616+00:00`, finished `2026-08-05T16:29:23.476095+00:00`,
  `status: failed`, `sha256_verified: false`, exit code 1 in the log, and one named
  `upload_failed:` path.
- `app/data/logs/backup_irreplaceable.out.log` records the preceding successful run
  `20260804T143449Z` finishing `2026-08-05T03:13:15.645391+00:00` with
  `sha256_verified: true` and `status: completed`.
- At Codex measurement time `2026-08-06T01:53:24Z`, the current failure was proved and the last
  successful completion was about 22h40m old.

Two Gemini phrasings are not yet confirmed and must not enter the catalog as facts:

1. The available marker/log names `upload_failed:<path>` but does not establish that the cause was a
   timeout. “Transaction JSON upload timeout” remains `UNVERIFIED` unless another timestamped log
   names that mechanism.
2. Gemini projected a 26-hour crossing at `2026-08-06T05:13:15Z` by adding 26 hours to the last
   successful completion. Governance `02` registers the backup rule against the scheduled 10:15
   local run/status-marker law; the exact alarm predicate and clock basis must be stated before that
   projected time is treated as a registered threshold crossing. The fresh failed marker is already
   a failed operational state; the countdown calculation is a separate claim.

The telemetry table also demonstrates why the catalog must separate job cadence from freshness
cadence: the feature-refresh LaunchAgent fires daily at 09:15, while
`app/config/report_freshness.json` registers the feature-refresh artifact with cadence `weekly` and
`dormant_ok: true`. Neither value supersedes the other; they answer different questions.

Gemini has delivered telemetry facts but has not yet issued the explicit operational-slice pass
David required for final inventory closure. No such pass is expected or inferred at increment 1.

Gemini's clarification supersedes two parts of its first report:

- It confirmed `backup_irreplaceable.err.log` is empty and no timestamped source names a timeout;
  the mechanism is correctly narrowed to the recorded `upload_failed:` path.
- It issued a five-element **OPS ALARM** on the separate deterministic predicate
  `status == "failed"`: observed failed value/timestamp; marker path; pre-existing standing backup
  law; predicate true; no declared paused dependent. Codex accepts the alarm as valid telemetry. It
  pauses nothing because Gemini found no registered dependent, authorizes no recovery action, and
  leaves every response to Claude/Codex/David. Manual backup runs remain David-gated.

The 26-hour projection is still not established as written. Gemini names the scheduled 10:15 local
run as the registered clock basis but calculates `05:13:15Z` by adding 26 hours to the preceding
successful run's completion time. Those are different clocks. Until the registered predicate says
which timestamp is the operand, the current failure is proved but that projected breach time is
`UNVERIFIED`.

Gemini also stated its ledger entry is the only durable copy of the operational table. The actual
ledger diff contains a three-bullet summary, not the detailed matrix rendered in the transcript.
Therefore the matrix itself is not yet durable and must be transferred into the canonical catalog
or a pinned evidence artifact before any operational-slice pass.

## Minimum row contract required for Codex verification

Each source row needs:

- stable `source_id`, provider/source family, paid/free/access method;
- licence and retention status, including the exact files/terms to which it applies;
- semantic role plus allowed and prohibited uses;
- meaningful-change cadence, distinct from pull/job cadence;
- evidence path/hash, `measured_at`, `verified_by`, and verification status.

Each stream row needs:

- stable `stream_id` and parent `source_id`;
- acquisition adapter/loader and arguments;
- source-vintage semantics and capture axis;
- scheduled/manual job and expected cadence;
- immutable raw landing and normalized landing;
- schema authority and every schema era;
- grain, identity key, identity coverage/conflicts, and unresolved-row treatment;
- last attempted pull, last successful pull, last byte/content change, and freshness verdict source;
- exports and exact consumer paths;
- lifecycle states kept separately: loader, contract, captured, normalized, exported, consumed,
  decision-supported;
- gap/disposition, evidence path/hash, `measured_at`, `verified_by`, and verification status.

Player 360 and semantic-metric rows must reference `stream_id`, exact schema field(s), transformation
path, unit/type/null semantics, provenance surfaced, freshness propagated, and every API/UI/model
consumer. A metric name without its source fields and formula is not an inventoried metric.

## Verification vocabulary

- `CONFIRMED`: reproduced from a pinned repo/disk/telemetry probe.
- `ATTRIBUTED`: another lane measured it; not independently reproduced here.
- `CONFLICTED`: two current artifacts or probes disagree.
- `UNVERIFIED`: claim or source exists, but the necessary evidence has not been established.
- `NOT_APPLICABLE`: dimension does not apply, with a stated reason.

`UNKNOWN`, blank, and `NO` are not interchangeable. No global catalog CLEAR is possible while a
required cell is blank or while a conflict lacks an explicit disposition.

## Next Codex increment

Freeze the post-commit target and then verify the catalog row-by-row, beginning with the mapping
between external sources, the 20 machine-registry definitions, every concrete adapter/loader, and
every physical raw/normalized store. Gemini's explicit operational pass will supply the independent
jobs/markers/freshness/cadence slice David required; it does not substitute for semantic review.
