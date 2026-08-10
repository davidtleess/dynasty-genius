# Footballguys `adp.csv` pilot framing v1 — Codex adversarial challenge

**Date:** 2026-08-09  
**Lane:** Codex, independent technical reviewer and prospective RED author  
**Artifacts reviewed:** `footballguys_adp_pilot_framing_claude_v1.md` and
`footballguys_adp_identity_false_match_measurement_claude_v1.md`  
**Artifact SHA-256s:** `9c492bb920122872ee4518c0b4f9a7e0b7dcd80a00ba35e74cda86ac423b2684`
and `34af5deea3d4be42a89076e41f048ccdd285b3504d954996142d11ae1037a4a8`  
**Layer:** 1 (ingest framing) with a demonstrated Layer-2 identity dependency; no layers 3–6
dependency check applies  
**Disposition:** **NOT CLEAR FOR RED OR INGESTION BUILD.** The measured export is overwhelmingly
consistent with ordinal ranks derived from ADP inputs, but the framing overstates that inference,
opens a semantic flip that cannot be earned from numeric shape, and leaves the horizon, comparison
cohort, baseline artifacts, retention boundary, and several non-vacuity contracts undefined. The
addendum then demonstrates a P0 silent-identity failure: 34 of 453 production-accepted IDs are the
wrong human and another 55 cannot be independently verified. The one-file pilot cannot detect this.
No redundancy result is valid on `canonical_resolved`; no ingestion RED opens.

No code, RED, intake, store, capture, provider contact, scheduler, commit, push, or redundancy
calculation was performed by this lane. The redundancy result remains unobserved so an identity
protocol and decision rule can be registered before it is run.

## Independent checks performed

Both submitted artifact hashes matched. A fresh read of the known local bundle reproduced:

- 30,388 raw bytes and SHA-256
  `1f7afcbfdd7b9c6d08dc21a0017f05d4a30fa64e0cd580c6295c5a5fc3a57eb9`;
- 608 rows, 19 columns, 608 distinct non-duplicate `id` values;
- 5,166 populated rank cells and zero decimal cells;
- all 17 populated market columns as exact `1..N` permutations; and
- `adp_sleeper-redraft` as a declared column with zero populated values.

The first rows also show the export is not merely sorted once and carrying one positional index:
the source columns disagree in player order while each independently remains a dense permutation.

Repository checks and the addendum changed the proposed RED boundary:

1. `app/data/identity/_runs/ff_playerids_20260516.json` contains 7,774 nonblank PFR IDs but only
   7,771 distinct PFR IDs. Three PFR IDs map to two different players apiece (`CartKy01`,
   `HarrAl00`, `MillSt00`). They do not occur in this 608-row vintage, but they prove a generic
   PFR lookup cannot use last-write-wins or assume uniqueness.
2. Production `IdentityIndex.from_governed_crosswalk()` does expose PFR-to-GSIS resolution and
   correctly holds IDs that map to multiple canonical players. Its conflict contract cannot detect
   a third-party PFR-like ID that uniquely maps to the wrong person, because uniqueness inside the
   governed crosswalk is not evidence that two providers use the same disambiguation counter.
3. The addendum ran those 608 source rows through that production resolver. Of 453
   `canonical_resolved` rows, 34 were provably the wrong human and 55 lacked the independent name
   evidence needed to verify them. The errors include ranks 1, 5, 6, 27, and 50 and are concentrated
   in the young players most material to the stated product use. Thus `canonical_resolved` is not a
   safe comparison-cohort state for this source namespace.

Official Footballguys material adds useful but non-dispositive context:

- a Footballguys staff administrator says Draft Dominator selects site-specific ADP inputs and may
  adjust them using Footballguys' own ranking movement for league settings such as 2QB:
  <https://forums.footballguys.com/threads/draft-dominator-where-does-it-pull-its-adp.812461/>;
- a different 2026 Footballguys dynasty product says its Sleeper ADP comes from dynasty league
  drafts: <https://www.footballguys.com/article/2026-dynasty-trade-value-chart-april>.

Neither page binds the exact Classic bundle field `adp_sleeper-sf` to a horizon or proves the
physical representation in this CSV. They support a plausible acquisition/transformation chain;
they do not close the field-level contract.

## Findings

### 1. Requested item 1 — a raw average can mathematically be a gapless permutation; the categorical proof fails

There is a steelman mechanism: if every observed draft used the same complete order, each player's
mean slot would be an integer and the means would be exactly `1..N`. Therefore *“cannot arise from
averaging”* is logically false. For a common complete player pool, reaching a permutation-valued
mean would in fact require that identical ordering; real ADP feeds can also use different sample
memberships and missing-player rules, so numeric shape alone still cannot prove the transformation.

That does **not** make the current export plausibly raw ADP. Seeing the same exact dense,
tie-free property in all 17 populated columns over 5,166 cells, with no decimal anywhere, is very
strong evidence of provider-side ordinalization. The official staff description makes this chain
plausible: source ADP → site/format selection → Footballguys adjustment → exported order.

**Required correction:** replace *“the file is not what its name says”* and *“cannot arise”* with:

> The exported values behave as ordinal rank positions derived from ADP inputs, not as retained
> raw mean draft slots. The export exposes an ordering but no spacing between players.

Keep a confidence label. Do not claim the provider lied or that ADP played no upstream role.

### 2. Requested item 2 — the pilot earns a gated identity/redundancy experiment, not an intake build

**Ruling: no ingestion build and no ingestion RED before the decision experiment.** The authorized
pilot can be satisfied first by a read-only, pre-registered comparison over the pinned local bytes.
Building provenance/storage/replay machinery before learning whether the only relevant column is
same-horizon and materially incremental spends Layer-1 effort on a candidate likely to close
`blocked_for_use`, repeating the `ff_rankings` sequence.

The addendum strengthens this ruling. A redundancy calculation performed first would be corrupted
by silently wrong joins. The next work, if David keeps the candidate alive, is a two-file read-only
decision experiment: `adp.csv` supplies the candidate ordering; `projections.csv` may supply only
name/team/position identity evidence. Projection values are not authorized as model signal.

Required order:

1. correct the physical-versus-semantic classification;
2. resolve the exact `adp_sleeper-sf` horizon;
3. pre-register a source-specific identity verification protocol and an exact baseline/decision
   contract;
4. classify every SF-populated row as `verified_same_human`, `verified_wrong_human`, or
   `unverifiable`, with no automatic acceptance from the PFR-like ID alone;
5. stop if the verified cohort floor fails; otherwise run redundancy only on
   `verified_same_human` rows with the same horizon; then
6. only if it survives, settle retention/backup and open a separate ingestion RED.

If the identity sidecar is unavailable or cannot be retained/used under the selected boundary, the
honest disposition is `blocked_for_use`, not a weakened comparison.

### 3. Requested item 3 — horizon is a gate for this pilot's claimed use

**Ruling: gate for redundancy, product selection, and any dynasty interpretation; caveat only for a
pure byte archive that David separately chooses.** A redraft rank can correlate with dynasty ECR for
reasons that say nothing about incremental dynasty-market value. Without a source-authentic mapping
of this exact field and vintage, F10 is not interpretable.

The empty `adp_sleeper-redraft` column and Footballguys' separate 2026 dynasty page are suggestive,
not proof. The latter describes another product and does not say that Classic
`adp_sleeper-sf` is the same feed. Framing v2 must supply exact provider documentation for this
field or record `horizon=unverified` and stop before redundancy.

### 4. Requested item 4 — F7 would turn numeric shape into an unearned semantic claim

F7 says one decimal must flip the recorded semantic to true ADP. A decimal proves only that a value
is not an integer ordinal. It could be a score, a transformed rank, a malformed cell, or another
provider measure. Likewise, ties/gaps do not prove raw ADP.

**Required correction:** separate physical shape from provider meaning. Suggested closed fields:

- `physical_value_shape`: `empty | dense_integer_permutation | non_dense_integer | decimal_numeric`;
- `provider_semantic`: `unverified | provider_declared_rank | provider_declared_adp`;
- `spacing_preserved`: `true | false | unverified`.

No observed shape may auto-promote `provider_semantic` to `provider_declared_adp`.

### 5. F4/F6 contain an actual vacuity: the empty column satisfies a naïve permutation test

The independent probe evaluated the ordinary predicate
`sorted(values) == list(range(1, len(values)+1))`; it returned **true** for the empty
`adp_sleeper-redraft` column. A GREEN can therefore label the empty lane a dense permutation while
also reporting zero coverage.

Required RED controls:

- empty column → shape `empty`, never dense-permutation `true`;
- one positive nonempty dense fixture → dense-permutation true;
- separate tie and gap mutants → false;
- declared header membership and stored schema membership asserted independently of coverage; and
- proof that dropping the empty column cannot pass by hardcoding a zero-count coverage record.

### 6. F5 can pass by using `max(rank)` as the populated count

On this vintage, `max(rank) == populated_count` in every populated column. A broken profiler can use
the maximum value instead of counting nonblank cells and reproduce every submitted number.

Required RED: a sparse fixture where nonblank count, maximum rank, distinct count, and total row
count are all different. Define raw coverage explicitly as `nonblank / total_file_rows`; for this
vintage the directly relevant lane is `500 / 608`. Do not let a comparison report silently replace
that denominator with the resolved intersection.

### 7. F1–F3 do not yet prove ordering, non-vacuity, or content identity

- Final raw artifacts do not prove raw retention occurred **before** parsing. Inject a parse failure
  after raw staging and specify whether the failed raw evidence is retained/quarantined; assert the
  order through that state transition.
- A refuse-every-changed-file implementation satisfies F3. Add a positive control: changed bytes
  under a new declared source version/date are accepted as a new observation.
- Reusing a content-addressed object must recompute byte count and full SHA from the stored object;
  trusting the filename or metadata repeats the B21 defect.
- A declaration needs field-level requirements (`provider`, product/bundle version, source-as-of
  date, David retrieval timestamp) plus negative controls proving archive mtime/build stamp cannot
  fill any missing declaration field.

### 8. F8/F9 would GREEN the demonstrated silent wrong-human joins

The addendum proves F8's resolution-count contract is unsafe, not merely incomplete. It would report
453 accepted rows while silently attaching at least 34 ranks to the wrong person. That is a 7.5%
known false-match rate among production-accepted IDs, not counting 55 accepted-but-unverifiable
rows. Three known errors are in the consensus top 25, seven in the top 50, and twelve in the top
100. Rank 1 resolving Jahmyr Gibbs to Jack Gibbens is sufficient by itself to fail the contract.

The file-wide census may report `resolved / 608`, but the redundancy study concerns the 500 rows
populated in `adp_sleeper-sf`. It needs a denominator ladder:

`608 file rows → 500 SF-populated → identity evidence available → verified same human →
same-horizon baseline matched → final comparison`.

Each loss requires IDs and a reason. Metrics computed only on the final intersection can otherwise
look excellent after dropping the hard cases.

Required identity contracts also include:

- the production status `canonical_resolved` is treated only as a candidate link for this source,
  never as proof of identity;
- PFR crosswalk conflicts fail closed (the pinned source proves conflicts exist generically);
- two source IDs mapping to one canonical player are conflicts, not two observations;
- duplicate source IDs are tested as both identical and conflicting rows;
- no last-write-wins path;
- exact, versioned normalization and evidence rules for names, nicknames, suffixes, teams, and
  positions; team/position disagreement quarantines rather than automatically declaring a wrong
  human because those fields can legitimately change; and
- accepted-but-unverifiable rows fail closed and never enter the redundancy cohort.

The hand-verified nickname whitelist is acceptable evidence for this bounded measurement only if
the exact whitelist is persisted and reviewable. It is not yet a production resolver contract.
Framing v2 must also preserve the complete 34 wrong mappings and 55 unverifiable IDs, or a
hash-bound machine-readable report containing them; examples plus totals are not independently
auditable enough for a promotion decision.

### 9. F10/F11 do not identify runnable baselines or a decision rule

`SOURCE_REGISTRY["ktc"]` currently says KTC is deferred until an official API exists. The framing
names KTC but supplies no exact local artifact, source date, SHA, identity key, or lawful acquisition
path. No RED may silently substitute FantasyCalc or fetch KTC at request time.

For each comparison, v2 must pin:

- exact source artifact and SHA;
- source-as-of date and maximum allowed vintage skew;
- semantic class (trade price, expert consensus, or ordinal rank);
- rank direction and tie method, especially if converting a price to rank;
- cohort floor and full attrition ladder;
- Spearman and top-24 definitions; and
- the ex ante disposition rule when the metrics disagree.

The prior `.99` result is evidence, not a threshold. “Pre-register a threshold” without actual
values and disagreement behavior does not prevent post-result rationalization.

Do not run this comparison until finding 8 is answered. Spearman and top-k overlap computed after
wrong-human joins would be precise measurements of a corrupted cohort.

### 10. F13/F14 leave retention and backup in contradiction

“Gitignored” is not a retention permission and “not committed” is not the end of copying. The
standing backup law would normally require an irreplaceable private store in the manifest, which
would create an offsite copy. Footballguys' current Terms restrict copying/reproduction and reserve
permission; this review does not make a legal conclusion about personal backup rights.

Required framing choice before any store:

- **scratch-only measurement:** retain only hashes, counts, cohort losses, metrics, and disposition;
  no durable raw store or manifest entry; or
- **durable private intake:** David explicitly settles local retention and offsite-backup treatment
  (and provider permission if needed) before the RED.

The current text simultaneously requires raw retention, forbids committing raw bytes, and invokes
the backup manifest without deciding whether offsite replication is allowed. That is not yet an
executable contract.

## Required v2 before re-review

1. Reword the headline as a high-confidence physical-shape finding, not a logical impossibility or
   provider-mislabel verdict.
2. Keep the ingestion RED closed and redefine the next action as a two-file, read-only
   identity/redundancy decision experiment, with `projections.csv` restricted to identity evidence.
3. Make exact-field dynasty horizon a gate for the comparison.
4. Replace F7's semantic auto-flip with separate physical and provider-declared semantics.
5. Replace F8/F9 with a fail-closed, source-specific identity-verification contract; persist the
   complete wrong/unverifiable census and set a minimum verified cohort before seeing redundancy.
6. Repair F4–F6 non-vacuity and F1–F3 ordering/positive controls.
7. Pin actual baseline artifacts and a complete pre-result decision rule; remove KTC unless a lawful,
   exact local artifact is named.
8. Choose scratch-only versus durable-retention/backup before any intake RED.

After a responsive v2, Codex can re-review the framing. If it clears, the next artifact is the
pre-registered read-only identity/redundancy contract—not an ingestion RED. H2 QB rushing remains a
registered hypothesis **UNDER TEST** with no result and is unrelated.
