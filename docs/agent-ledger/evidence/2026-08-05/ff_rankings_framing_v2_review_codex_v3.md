# `ff_rankings` corrected framing v2 — Codex re-review v3

**Date:** 2026-08-05  
**Lane:** Codex, independent technical reviewer  
**Artifact reviewed:** `ff_rankings_disposition_claude_v2.md`  
**Prior artifact:** `ff_rankings_framing_challenge_codex_v2.md`  
**Layer:** Layer 1 ingestion framing, with Layer 2 identity and expert-consensus overlay boundaries  
**Disposition:** **NOT CLEAR FOR RED.** Claude's dispositions close C1–C9, but the corrected framing's
proposed redundancy gate is now partly answered by existing pinned evidence and a fresh read-only
comparison. The result changes the next question; it does not yet define a build.

No StreamSpec, RED, GREEN, source/test/fixture edit, capture, store write, scheduler, consumer,
commit, or push was performed.

## 1. C1–C9 disposition audit

All nine dispositions are accepted as responsive. v1 is correctly withdrawn. In particular:

- the same-source-family and non-price correction is explicit;
- `type="all"` is no longer hidden by the two-stream claim;
- direct Superflex is separated from mixed dynasty pages;
- existing destination (b) is retired;
- raw evidence is separated from normalized/product use;
- identity is correctly split between Layer 1 raw and Layer 2 canonicalization;
- source vintage is separated from observation time; and
- the historical archive is recognized as its own schema/grain problem.

Those closures stand. The findings below concern corrected framing v2's new gate.

## 2. R2-F1 — the proposed redundancy experiment is valid only at raw-source level, and it is now run

The local `dp_archive` table cannot itself support an honest same-vintage comparison:

- it stores `value_2qb` and no `overall_rank` for these rows;
- its `snapshot_date` is the backtest fold target date, not the original source `scrape_date`;
- its loader discards original `fp_id`, source scrape date, and archive publish date after PIT
  admission; and
- `value_2qb` is a monotonic exponential transform, not the raw ECR measurement.

The comparison was therefore run read-only against the four already pinned raw `values.csv` files
in `/var/tmp/dp-values/` (their SHA-256 values re-match the registration) and
`nflreadpy.load_ff_rankings(type="all")`. Each comparison used the exact `values.csv` source
`scrape_date`, filtered `ff_rankings` to `page_type=dynasty-op` and `ecr_type=dsf`, joined
`id ↔ fp_id`, and compared direct `ecr` to `ecr_2qb`.

| Target | Source vintage | Joined | Exact ECR equality | Spearman | Kendall | Median absolute rank gap | Top-24 overlap |
|---|---|---:|---:|---:|---:|---:|---:|
| 2021-09-08 | 2021-09-03 | 479 | 48 | 0.9950 | 0.9503 | 3.51 | 23/24 |
| 2022-09-08 | 2022-09-02 | 484 | 42 | 0.9909 | 0.9327 | 4.56 | 23/24 |
| 2023-09-08 | 2023-09-08 | 444 | 19 | 0.9723 | 0.8820 | 8.76 | 21/24 |
| 2024-09-08 | 2024-09-06 | 396 | 134 | 0.9794 | 0.9513 | 0.03 | 23/24 |

The `value_2qb` formula independently reproduced exactly on every joined row:
`round(10500 × exp(-0.0235 × ecr_2qb))`.

This agrees with the repo's already recorded methodology evidence:
`dp_archive.ecr_2qb` is a LOESS-based 1QB→2QB/Superflex transformation, while `dynasty-op/dsf` is
the direct FantasyPros Superflex expert-consensus page
(`docs/agent-ledger/evidence/2026-07-25/codex_market_measurement_verdict.md:223-260`).

**Finding:** the two are highly correlated but **not the same instrument**. Therefore the binary
question “same instrument → redundant; otherwise useful” is not a valid decision rule. Direct `dsf`
is a real semantic increment over a synthetic 2QB transform, but usefulness/landing does not follow
from non-identity.

## 3. R2-F2 — a product-use/materiality criterion is still missing

The experiment shows both sides of the problem:

- direct `dsf` is methodologically cleaner for the exact Superflex construct;
- top-of-board ordering is extremely similar (21–23 of the top 24 overlap);
- tail differences can be large; and
- `ff_rankings` additionally carries dispersion fields (`sd`, `best`, `worst`) absent from the
  integrated transformed-value series.

Framing v3 must state which concrete decision these increments serve and what result would justify
storage. Candidate questions are not interchangeable:

1. direct-Superflex expert benchmark for model rank validation;
2. expert-disagreement/uncertainty history from `sd/best/worst`;
3. weekly consensus-movement history; or
4. a David-facing current overlay.

The first three can justify a research/validation substrate; the fourth additionally requires a
consumer contract, identity, freshness, and No-Verdict surface controls. “It differs” is not a
consumer or an edge claim.

## 4. R2-F3 — `dynasty-rk` is not established as Superflex-relevant

v2 says David's directly relevant slice is 540 `dynasty-op` rows **plus 115 `dynasty-rk` rows**.
The evidence proves only:

- `dynasty-op` → `dynasty-superflex.php`, `ecr_type=dsf`;
- `dynasty-rk` → `rookies.php`, `ecr_type=drk`.

Nothing in the payload labels the rookie page Superflex/2QB. It may be useful as general rookie
expert consensus, but it cannot be included in the exact-league Superflex cohort without separate
format evidence. Until then, the directly proven Superflex slice is 540 rows, not 655.

## 5. R2-F4 — “finer cadence” conflates source capability with local integration

Both DynastyProcess outputs are built by the same upstream weekly Friday workflow. `type="all"`
already carries the historical weekly source vintages; `values.csv` git history can also be replayed
weekly. The current local `dp_archive` integration happens to retain only four fold dates.

The increment is therefore **broader local historical integration and different source fields**, not
an independently finer upstream cadence. A future framing must say which is being compared:

- source capability/cadence; or
- rows currently materialized in Dynasty Genius.

Forward capture should trigger on a new upstream source vintage/content hash, not on an invented
daily schedule.

## 6. R2-F5 — destination and license remain blockers, not RED details

Because this is expert consensus rather than a trade-price series, a generic “market store” risks
recreating the semantic collapse v2 corrected. If selected, prefer an explicitly named separated
expert-consensus/DynastyProcess store, or a generic overlay store with hard source-class partitions
that cannot represent ECR as trade value.

The exact-file retention question is still unresolved. The repo's 2026-07-25 source sweep records
GPL-3.0 at repository level, no separate data license, and requires an explicit decision before
durable ingestion/committed or distributed derived data. FantasyPros underlying terms remain
unestablished. A RED for durable capture cannot silently assume that decision.

## 7. Direct answers to v2 §C

1. **Is redundancy versus `dp_archive` the right gate?** Capability equivalence is the right first
   measurement, but binary equality is the wrong landing rule. The measurement is now run: direct
   `dsf` is not identical to the transformed `ecr_2qb` series.
2. **Is `dsf` a genuine increment?** Semantically, yes: direct Superflex consensus versus a
   LOESS-derived 2QB transform. Product/predictive value remains unestablished; high top-24 overlap
   warns against treating difference as usefulness.
3. **Does “no disposition yet” satisfy the landing rule?** Yes at framing time: the board says every
   stream states its disposition **at landing**. “No disposition” honestly keeps landing closed. It
   does not provide a concrete target for an ingestion RED.
4. **Is this justified before Layer 2?** A byte-faithful research/raw archive can technically remain
   Layer 1, but whether it outranks Layer 2 for this product is David's unresolved sequencing choice.
   Identity and consumer normalization cannot be smuggled into that raw scope.

## 8. Required next framing step

**Do not open a RED yet.** Route a concise v3 that:

- replaces the now-answered binary redundancy gate with the measured direct-vs-transformed result;
- removes `dynasty-rk` from the proven Superflex cohort unless format evidence is supplied;
- selects one concrete decision/use for the direct `dsf`/dispersion/history increment;
- distinguishes weekly source cadence from four-date local materialization;
- names the expert-consensus storage class without relabeling it trade market;
- records the license/retention decision as a blocker; and
- carries David's answer on whether Layer 1 raw expert-consensus history should precede Layer 2.

If David chooses not to prioritize it or retention remains unresolved, the honest disposition is
`blocked_for_use` with no RED. If David selects a research-only Layer 1 substrate and settles the
retention boundary, the later RED should be limited to raw/history acquisition and provenance; no
identity, normalized overlay, consumer, scheduler, or David-facing surface enters that scope.

Contracts remains separately parked at pinned v16 pending David's commit word. This review grants
no action authority. H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result.
