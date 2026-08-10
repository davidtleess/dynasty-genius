# Footballguys `adp.csv` pilot framing v2 — Codex round-2 review

**Date:** 2026-08-09  
**Lane:** Codex, independent technical reviewer / prospective RED author  
**Artifact reviewed:** `footballguys_adp_pilot_framing_claude_v2.md`  
**Artifact SHA-256:** `bca2c0dc7123b58ae8810cae0c6b4b11c74fdee93866c5f6daf1d3cb31072aa1`  
**Identity census reviewed:** `footballguys_adp_identity_census_claude_v1.json`  
**Census SHA-256:** `2f2feca4678d90df665b6943cec03b07e34ca5e2a3fe46a367b440e6e69a5558`  
**Disposition:** **NOT CLEAR.** Ingestion RED remains closed. V2 materially improves the framing and
correctly stops at the failed horizon gate, but the identity evidence, cohort gate, baseline pin,
top-k estimand, vintage alignment, and scratch-only retention contract are not yet executable or
internally consistent.

No provider contact, intake, store, model input, surface, scheduler, RED, commit, push, or new
redundancy run was performed by this lane. The known bundle was parsed read-only; nothing in it was
executed.

## Findings

### 1. The ten acceptances are responsive, but §1 reintroduces an unsupported averaging claim

The revised headline is substantially correct: the export behaves as ordinal positions derived
from ADP inputs and exposes no player-to-player spacing. The categorical provider-mislabel claim is
properly withdrawn.

Delete or qualify: *"Less restrictively, distinct orders can still average to distinct integers."*
For a common complete player pool, a convex average of draft-order permutations can equal another
permutation only when every positively weighted order is that same permutation. Variable player
pools/missing-player rules can create other constructions, but v2 does not specify one. Do not let
the sentence imply a less restrictive mechanism for the observed exact `1..N` result.

Also prefer *"the export exposes an ordering but no spacing"* to *"preserves order"*: the staff
description permits Footballguys adjustments, so upstream raw-ADP order preservation is not proved.

### 2. The census totals reconcile, but the artifact is not the complete identity evidence v2 claims

Verified from the JSON:

- 608 rows and 608 distinct source IDs;
- 500 SF-populated rows;
- all-row verdicts `364 same / 34 wrong / 55 unverifiable / 155 unresolved`;
- SF verdicts `328 same / 32 wrong / 47 unverifiable / 93 unresolved`; and
- zero duplicate non-null candidate GSIS groups.

But only 39 rows carry all of `provider_name`, `provider_pos`, `provider_team`, `our_name`, and
`reason`. Another 359 same-human rows omit `reason`; all 210 unresolved/unverifiable rows omit the
provider attributes and `our_name`. This directly contradicts §5.2's statement that every row
carries those fields.

The omission is not merely unavoidable missingness. Of the 155 `unresolved` rows, **136 have a row
in `projections.csv`; 78 of those are SF-populated**. For example `StBrAm00`, `CookJa05`,
`BrowCh06`, `WalkKe01`, `HallBr01`, and `JacoJo00` all have provider name/position/team evidence,
but the census drops it because production PFR resolution failed.

The census also pins only the `adp.csv` hash and a filesystem path for the governed crosswalk. It
does not pin the `projections.csv` SHA/bytes, governed-crosswalk SHA, normalizer version/exact rules,
or generator/query. A hash of the output does not make the classification reproducible.

Required v3:

- use a uniform row schema with explicit nulls and a reason on every row;
- populate provider attributes independently of whether the candidate link resolved;
- pin both input-file hashes, the crosswalk hash, exact normalization/suffix rules, and whitelist;
- pin the source of **our** name, position, and team attributes; and
- define the position/team comparison and quarantine rules. Current crosswalk evidence supplies a
  position but no team, and the census carries neither `our_pos` nor `our_team`, so §5.1's claimed
  position/team check is not executable and the current 328 cannot yet be called protocol-verified.

### 3. Ruling A — replace the compromised 80% number with a two-stage, composition-aware floor

The current vintage fails regardless of any reasonable threshold: identity exclusions are known to
be nonrandom and hit ranks 1, 5, 6, 27, and 50 in the consensus ordering. A numeric floor must not
launder that structural failure.

For a genuinely unseen future vintage, Codex sets the prospective gates as follows:

1. **Identity gate:** `verified_same_human / SF-populated >= 90%` (**at least 450/500**).
2. **Decision-region gate:** identity must be verified for **100% of the union of both sources'
   top-24 candidates**, and for at least **95% of Footballguys ranks 1–100**.
3. **Composition gate:** identity coverage must be at least **85% in every predeclared rank band
   (`1–24`, `25–50`, `51–100`, `101–200`, `201–500`) and every position/experience stratum with
   n>=20**. Pin the experience source and buckets before access; reporting a skew without a pass/fail
   rule is not a gate.
4. **Final matched-cohort gate:** after same-horizon FantasyCalc matching, at least **80% of the
   original SF slice** must remain (**at least 400/500**). The denominator never resets to verified
   or matched rows.

These are data-fitness gates, not correlation thresholds. They are set after seeing this vintage's
identity failure and therefore cannot rehabilitate this vintage. They govern only an unseen future
aligned vintage. Current state (`328/500` identity-verified; `285/500` in the disclosed comparison)
fails before any statistic.

### 4. The FantasyCalc baseline is identified but not reproducibly pinned

The snapshot facts are independently supported: 475 rows, one `retrieved_at`, one settings hash,
475 populated distinct Sleeper IDs, and 47 daily snapshots through 2026-08-09. Residuals:

- pin `settings_hash=e27351d720e9fcf0` explicitly;
- the ordered-content SHA needs the exact SELECT columns, WHERE clause, ORDER BY, null encoding,
  serialization, and line-ending recipe. `deterministic, ordered` is not a reproduction contract;
- `475 distinct payload_hash` values do not establish a single capture; the single shared
  `retrieved_at` does. State the facts without implying a snapshot-wide payload digest;
- *"39 tied values"* is inaccurate. There are **34 duplicated-value groups, 73 rows participating
  in ties, and 39 duplicate rows beyond the 436 distinct values**. Choose and name one measure.

### 5. Vintage alignment and the top-24 decision rule remain internally incomplete

The baseline table says `max vintage skew = 0 days`, then says the candidate/baseline skew is four
days and a ceiling still must be declared. Those cannot all stand. Worse, the four days compare a
Footballguys bundle/build stamp with FantasyCalc `retrieved_at`; §6.3 correctly says a build stamp
cannot substitute for David retrieval provenance. Different timestamp semantics do not establish
source-vintage skew.

V3 must define the two comparable as-of fields, their sources, timezone/cutoff, and one prospective
maximum. If the maximum is zero, the current pairing simply fails.

The top-24 rule also does not define its estimand. The disclosed 22/24 is obtained by reranking the
survivor cohort. Original source membership (`rank <= 24`) leaves 16 verified/matched candidates
from each side and 14 common IDs. V3 must state whether top-k is original-source membership or
survivor-reranked; only the former answers ordinary top-24 overlap. Define the exact denominator,
tie-at-boundary behavior, missing-identity treatment, top-24 threshold bands, and every
Spearman/top-24 combination. *"More conservative governs"* plus one example is not a complete
decision table.

### 6. Ruling B — accept permanent non-load-bearing status, with explicit supersession

The proposed remedy is correct with these amendments:

- Preserve `0.9670 / n=285 / 22-of-24` as an audit-trail exploratory observation with
  `invalidated_for_decision=true` and `decision_supported=false`.
- Explicitly supersede both the result artifact's `REDUNDANT` band selection and *"Redundancy is
  established for the verified core."* Withdrawal in a later artifact is not enough if the earlier
  claims remain unlabeled.
- Reconcile its ladder as `500 -> 93 source_only -> 47 no name evidence -> 35 exact-name
  mismatches (32 wrong humans + three verified same-human variants) -> 2 other no-Sleeper-ID -> 38
  absent FC -> 285`. The exact rho `0.9669669841` is reconstructible after that unregistered
  exclusion rule was disclosed.
- Preserve the same-human-inclusive sensitivity (`n=287`, `rho=0.9666705246`) and both top-k
  definitions. Neither is load-bearing.
- A rerun on the same already-seen bytes is not fresh. Only a genuinely unseen future Footballguys
  vintage with an aligned FantasyCalc snapshot, after horizon and every v3 gate are frozen, can be
  confirmatory.

Recording the premature run as a falsification miss is appropriate. It is not characterized as
defiance of a later instruction or as evidence of post-result threshold selection.

### 7. The scratch-only retention choice contradicts the durable census

The 181,350-byte census is a row-level derivative containing all 608 provider IDs, both source rank
fields, and hundreds of provider names/positions/teams. V2 calls it committed evidence while also
claiming no durable provider-data store, no offsite replication, and no provider-permission
question. Committing/pushing that artifact is durable offsite replication of provider-derived data
even if the original CSV bytes are absent.

Choose one before landing the census:

- **true scratch-only:** durable evidence is minimized to input hashes, aggregate counts, metric
  outputs, disposition, and a privacy/content-minimized audit of exceptional IDs sufficient for
  review; no full 608-row ranks/attributes artifact is committed or pushed; or
- **durable derived evidence:** explicitly acknowledge the row-level retention and have David settle
  its local/offsite treatment and any provider-permission boundary.

This review makes no legal conclusion. It rejects only the factual claim that the current census is
non-durable scratch evidence.

### 8. The dominance comparison stands narrowly, not as redundancy proof

The operational/source-fitness comparison stands after correcting the tie wording: locally held
FantasyCalc preserves price spacing, is current across 47 daily snapshots, uses native Sleeper IDs,
has a declared dynasty-trade construct, and is the registered primary market signal. The observed
Footballguys candidate is one manual, rank-only artifact with unsafe identity and unverified
horizon. Those facts are a strong independent reason not to build this candidate now.

They do not establish informational dominance, same-construct redundancy, or zero incremental
value. If the exact Footballguys field is dynasty-startup draft behavior, it may measure a construct
that trade price does not subsume. The horizon gate correctly prevents that inference.

## Required v3 before round 3

1. Correct §1's averaging/order wording.
2. Repair and fully pin the uniform identity census and executable attribute-verification rules.
3. Adopt the prospective cohort gates in finding 3; current vintage remains failed/non-load-bearing.
4. Make the FantasyCalc content pin reproducible and correct the tie metric.
5. Resolve vintage timestamp semantics and fully define top-24/tie/disagreement behavior.
6. Apply the result supersession labels and corrected ladder.
7. Resolve scratch-only versus durable row-level derived evidence before commit/push.

The horizon gate remains failed, so no provider comparison, ingestion RED, or build opens. H2 QB
rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
