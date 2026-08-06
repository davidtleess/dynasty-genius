# Layer 1 Feature-Refresh Route Pressure Test — Codex v3

**Observed:** 2026-08-05 22:43 EDT

**Scope:** planning only. No capture, store, scheduler, paid call, consumer, model, commit, push, or
backup execution was performed. David separately resolved the backup question with *“i meant RUN
IT”* for the next session.

## Outcome first

**Recommendation: Option A for all five streams, with different physical/cadence policies by
stream.** `player_stats`, `rosters`, `snap_counts`, `pbp`, and `participation` should each have one
canonical Layer 1 capture route. The 09:15 Feature Refresh should consume one atomic, provenance-
pinned last-good bundle and make no external source calls.

This is not a recommendation to put five full-history JSON copies into the existing raw directory
every morning. Exact upstream Parquet bytes should be content-addressed and retained only when
content changes. Current-season partitions may be checked frequently; closed historical seasons
should be revalidated on a slower measured cadence. PBP and participation may use partitioned
normalized projections, but aggregation cannot replace the exact raw source artifact.

No stream makes Option B — a live provider read inside derivation — the better authoritative route.
The legitimate volume concern changes the capture representation and cadence, not the lineage.

## 1. Steelman of Option B and the measured answer

The strongest B case is PBP/participation volume, not simplicity. The daily process is a fresh
process and nflreadpy 0.1.5 defaults to memory-only caching, so today it downloads all requested
files again on every run. Live source bytes for the exact default completed-season window were
measured from the nflverse release assets at 22:36–22:38 EDT:

| Stream | Seasons requested | Rows | Exact source bytes | MiB | Share of bytes |
| :-- | :-- | --: | --: | --: | --: |
| player_stats | 2018–2025 | 147,223 | 6,648,758 | 6.34 | 3.35% |
| rosters | 2018–2025 | 24,862 | 4,563,442 | 4.35 | 2.30% |
| snap_counts | 2018–2025 | 205,354 | 1,856,232 | 1.77 | 0.94% |
| pbp | 2018–2025 | 389,358 | 159,634,072 | 152.24 | 80.41% |
| participation | 2019–2025 | 334,682 | 25,818,556 | 24.62 | 13.01% |
| **Total** | | **1,101,479** | **198,521,060** | **189.32** | **100%** |

If unchanged full-history bytes were copied once per day, the source-byte floor alone would add
5.55 GiB per 30 days and 67.48 GiB per year. That would be a bad A implementation. It is also close
to the network work B already performs: the current daily job has no persistent cross-process
cache.

The provider exposes stable `ETag` and `Last-Modified` values on the release asset. A measured
conditional request for `play_by_play_2025.parquet` returned HTTP 304 with zero payload when sent
the observed ETag. Therefore an A capture can check partitions without re-downloading unchanged
bytes; B's repeated full download is not a volume advantage.

For the current 2025 partitions alone, all five source files total 143,125 rows and 26,765,321 bytes
(25.53 MiB). That is the bounded high-change frontier under the measured completed-season window,
not a prediction of future cadence.

## 2. Storage and backup pressure

The latest retained backup staging inventory contains 482 files and 1,994,594,012 bytes. One exact
eight-year baseline of these five streams would add 198,521,060 bytes, or 9.95%, if classified as
protected/irreplaceable. A new full current-season version at today's 2025 sizes is 25.53 MiB.
Actual cloud cost remains `UNVERIFIED`; no claim of affordability is made.

The existing generic JSON snapshot shape is not suitable for the large streams. One latest JSON
envelope for each 2018–2025 snap-count season occupies 68,904,107 bytes (65.71 MiB), 37.12 times the
1,856,232 source-Parquet bytes. There are 129 snap-count raw JSON files totaling about 1.0 GiB, and
the full existing `app/data/nflverse_usage/raw` tree is about 5.2 GiB. Automation must not repeat
that expansion pattern for PBP.

The current backup manifest excludes `app/data/nflverse_usage.db` as rebuildable and does not
protect `app/data/nflverse_usage/raw`. That is insufficient for an exact prior-vintage replay once
an upstream asset at the same logical URL changes. Before enablement, David must choose one of two
honest retention contracts:

1. protect content-addressed exact source bytes as irreplaceable replay evidence; or
2. explicitly accept that only the provider's current version is recoverable and that historical
   byte-exact replay can be lost.

The recommendation is (1), after the already-authorized backup recovery succeeds and with a
numeric storage/run-rate ceiling. Unchanged bytes are never copied again.

## 3. What Option A changes in the feature job

Today `_load_source` downloads all five sources before it computes one combined source hash. Under
A, it would load the governed bundle instead. The behavior changes are:

- **Network failure:** today a timeout/404 can abort the derivation. The log contains one recorded
  full-run refusal caused by a participation download timeout. Under A, capture fails and preserves
  last-good; the downstream job can still run against the prior bundle while disclosing staleness.
- **Freshness:** today successful reads are whatever the provider serves at that moment. Under A,
  freshness becomes the capture marker's source vintage. To avoid an accidental one-cycle lag,
  capture must precede Feature Refresh and its cadence must be based on measured upstream publish
  times, which are not yet pinned.
- **Season advance:** the code deliberately advances when a new season appears in `player_stats`.
  The other feeds have different availability, especially participation. A must publish one bundle
  with an explicit coherent season frontier or an explicit per-feature missingness contract; it
  must not silently combine new player stats/PBP with stale participation.
- **Noop semantics:** today the report stores one irreversible combined content hash, not the five
  source artifacts or their individual hashes. Under A, the bundle manifest supplies per-stream
  SHA, source vintage/HTTP validators, capture time, season partitions, and schema version.
- **Data types:** canonical exports must preserve the loader-facing schema expected by the feature
  builder. Conversion controls are required before replacing any live frame.

The job does depend on same-day provider state when the new season becomes available: its own code
says it should advance “the moment real new-season data lands.” A preserves that intent only if the
capture schedule runs first and the bundle gate recognizes the new coherent frontier.

## 4. Per-stream mixing

Mixing **capture policies** is legitimate; mixing **authoritative routes** is not.

- player_stats and rosters: canonical raw bytes plus normalized season partitions.
- snap_counts: use the canonical stream/export that already exists; remove the live read.
- pbp and participation: exact content-addressed Parquet raw, conditional checks, and partitioned
  normalized data. A bounded active-season polling window plus slower historical revalidation is
  appropriate once source cadence is measured.

“Aggregate on capture and discard raw” is not acceptable: it destroys replay and violates the
raw-before-parse rule. A consumer-specific projection may coexist downstream of one raw artifact,
but no consumer may fall back to a second live route.

## 5. The snap-count double route

The direct read is the duplicate. Canonical B4 already contains 253,106 rows for 2016–2025 and has
a ready-manifest-pinned Parquet export. For the Feature Refresh window, the current live source and
canonical export both contain exactly 205,354 rows. A value comparison over all 16 source columns
passed after sorting; the only schema difference is intentional integer widening (`season` and
`week`, Int32 live versus Int64 export).

The feature builder uses only `pfr_player_id`, `season`, and `offense_pct` from this stream. On the
same vintage, replacing the live frame with the canonical export therefore does not change
`snap_share` values. A full read-only assembly comparison then substituted canonical B4 for the live
snap frame while holding all other inputs fixed: both candidates were 2,743 rows × 39 columns and
were value-identical after deterministic player/season sorting (dtype differences ignored at the
input boundary). What must be added is a governed loader and a durable candidate-equivalence
control. What changes operationally is desirable: loss of the live network dependency and explicit
last-good provenance.

## 6. Replayability under Option B

Yesterday's Feature Refresh cannot be reproduced exactly from current artifacts if the provider
bytes change.

The repo retains the derived runtime/candidate and a combined `source_hash`, but not the five input
frames, their individual hashes, their release-asset validators, or a provider vintage. The latest
report is updated on changed-source publish, while noop runs do not write a new terminal report.
`nextgen_export_provenance.json` identifies only the already-local NGS bundle. A hash can verify a
candidate source set if the same bytes happen to remain available; it cannot reconstruct those
bytes.

Therefore B loses byte-exact source replay, per-stream lineage, independent schema-drift diagnosis,
and the ability to distinguish a provider correction from a code/config change. It fails the
constitution's reproducibility tenet and the architecture's raw-snapshot-before-parsing rule.

## 7. Recommended staged decision

1. Recover and verify the governed backup under David's explicit “RUN IT” authority.
2. Close the complete Layer 1 inventory; this pressure test does not waive that gate.
3. Make snap_counts the first migration because the canonical data already exists and value parity
   plus full candidate parity are measured.
4. Design the other four as canonical streams with content-addressed exact Parquet, conditional
   checks, per-partition hashes, atomic bundle publication, and no unchanged snapshot.
5. Pre-register source cadence/season-frontier rules and numeric storage/transfer ceilings before
   enabling schedules.
6. Run candidate byte/value equivalence on a pinned common bundle, then remove all five direct
   external reads. No fallback to the live provider remains inside Feature Refresh.

This is a planning recommendation, not build or enablement authority. Layer 2 remains closed. H2 QB
rushing remains a registered hypothesis **UNDER TEST** with no result.
