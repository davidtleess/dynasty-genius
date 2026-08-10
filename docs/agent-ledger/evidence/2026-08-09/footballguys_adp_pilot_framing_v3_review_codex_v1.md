# Footballguys `adp.csv` pilot framing v3 — Codex round-3 review

**Date:** 2026-08-09  
**Lane:** Codex, independent technical reviewer / prospective RED author  
**Artifact reviewed:** `footballguys_adp_pilot_framing_claude_v3.md`  
**Artifact SHA-256:** `5a6ed5a96c2f10cd6d03703090306220d7130fee5bb53b20b3d531d1a943ef64`  
**Generator reviewed:** `footballguys_identity_census_generator_v2.py`  
**Generator SHA-256:** `1d91925a5f5a2a7d9910eff6e3981babf45c9a7c480a5adf08ddfb69e1e4c5dd`  
**Disposition:** **NOT CLEAR.** V3 closes most analytical defects, and the minimized/full generator
outputs reproduce the submitted counts. Four bounded protocol/code defects remain. Ingestion RED
stays closed; horizon and cohort gates remain failed.

No provider contact, intake, durable store, model input, surface, scheduler, RED, commit, push, or
new redundancy comparison was performed by this lane. The submitted evidence generator was run
against the pinned scratch inputs solely to validate its outputs.

## Independent checks that passed

- Framing, generator, and minimized-artifact hashes/bytes match.
- Default generation reproduced the minimized artifact byte-for-byte: 13,853 bytes, SHA-256
  `549b04fe5104a6cf9c2900953321a8b484d6d49a2a923e46efbf0fb2c532244a`.
- `--full` produced 608 rows / 608 distinct source IDs with one uniform 15-field row schema;
  all 136/155 unresolved rows with projection evidence are now populated, including 78/93 SF.
- Verdict totals remain `364 same / 34 wrong / 155 unresolved / 55 unverifiable` file-wide and
  `328 / 32 / 93 / 47` in the SF slice.
- All 364 name-verified rows have matching position; among 34 known wrong-human links, position
  differs on 32 and agrees on two.
- The current full output is 270,884 bytes, SHA-256
  `3bfde88a8c70890da33d103a786fea0fa86c56170224bce3b064ad32c34ec1aa`.
- The FantasyCalc SQL recipe reproduces `f6f08b23714844f1df368b69fd9aa4f271492af2a930121b44fbf1ec021c05d5`
  when `rows` means SQLite's ordered positional tuples in SELECT-column order.
- The redundancy result now has a prominent supersession banner, both earlier findings are
  explicitly withdrawn, and both 500-row ladders reconcile.

## Findings

### 1. The generator reports pins but does not enforce them, and `--full` is dangerously mislabeled

The generator computes and records the three input hashes, but it has no expected-hash constants or
declaration check. Passing changed `adp.csv`, `projections.csv`, or a changed governed crosswalk
silently produces a different census rather than refusing. That is not regeneration from pinned
inputs; it is ungoverned regeneration with hashes printed afterward.

Worse, `retention_note` is unconditional. A `--full` run emits all 608 provider IDs/ranks/names/
positions/teams while its own metadata still begins:

> `MINIMIZED: no provider ranks/names/positions/teams are reproduced...`

That label is false on the high-risk output mode and could cause the full artifact to be handled as
commit-safe.

Required v4 generator controls:

- fail closed unless current `adp.csv`, `projections.csv`, and crosswalk hashes/bytes equal the
  declared current-vintage pins; a future vintage requires a new declaration, not silent drift;
- record and pin the generator version/hash and production resolver module hash (current
  `src/dynasty_genius/nflverse_usage.py` SHA-256
  `5ee7cbb54c2682ef00e6885df5e4ff41acb8030deddf69a9e2c33748400af6c0`), because the generator
  imports mutable production logic;
- make the full-mode retention label explicit: `SCRATCH_ONLY_FULL_PROVIDER_DERIVATIVE`, with a
  refusal to write inside the repository or another durable root;
- make minimized/full metadata conditional and accurate; and
- record the expected full-output SHA/bytes after the corrected generator is frozen, so
  “byte-for-byte” has an actual comparison target.

Also correct v3's scope sentence: a 133-line executable Python evidence generator was authored and
run. It is evidence tooling, not product/intake code, but *"No code"* is factually false, and
`committed generator/artifact` should read `commit-intended` until a commit exists.

### 2. Census-minimization ruling — keep the 34 mappings, but remove ranks and hash the large ID lists

Do **not** land the full census and do **not** seek a broader durable-data ruling for it. The
complete-but-regenerable / minimal-but-committed architecture is the right choice after finding 1
is repaired.

The minimized artifact still contradicts v3's claim *"No ADP ranks"*: every wrong-human mapping
contains `sf_rank` and `consensus_rank`. It also durably copies 55 unverifiable and 155 unresolved
source IDs even though the generator can reproduce them locally.

Codex's required durable minimum is:

- retain the **34 wrong-human mappings** because they are the concrete evidence for the defect;
  keep only `source_id`, `candidate_gsis`, provider/crosswalk names, and provider/crosswalk
  positions needed to prove the mismatch and position-guard result;
- remove per-row `sf_rank` and `consensus_rank`; retain only aggregate concentration counts
  (`top-25`, `top-50`, `top-100`, `top-200`) if that result remains cited;
- replace the 55- and 155-ID arrays with `{count, sorted_ids_sha256}` commitments; the corrected
  scratch-only full generator supplies the inspectable lists when authorized locally;
- include minimized-output, expected-full-output, generator, resolver, and all input hashes in the
  method block; and
- use a repo-relative crosswalk path, not `/Users/...`, so the artifact is clone-portable.

This is the answer to the requested minimization question. It preserves falsifiable defect evidence
without landing the licensed rank payload or the complete exception population.

### 3. The position experiment supports a narrower conclusion than v3 states

The measurement establishes:

- position alone is insufficient: it misses two of 34 known wrong-human links; and
- position is a useful corroborating/quarantine field.

It does **not** establish that position is necessary or that name is insufficient. On this vintage,
the normalized-name/whitelist rule already separates all 34 known wrong humans, while position adds
no newly detected error. The “mutation test” is also an evaluation over rows selected by the known
name mismatch, not a code mutation test.

Keep name + position as a prudent future contract, but change the evidentiary conclusion to:

> Exact normalized name/whitelist is the primary verifier in this vintage. Position is required as
> corroboration and quarantines a future name agreement with position disagreement. Position-only
> resolution is prohibited and empirically misses 2/34 known wrong links.

Team remains unavailable and untested; that limitation is now honestly stated and is not itself a
clearance blocker.

### 4. Vintage and top-k execution rules remain asserted rather than fully defined

`David-declared Footballguys retrieval timestamp` and FantasyCalc `retrieved_at` are acquisition
timestamps, not provider effective/as-of dates. Call the <=7-day rule a **retrieval-alignment
ceiling**. It does not prove source-vintage equivalence. If provider-authentic effective dates later
exist, define a separate as-of-to-as-of ceiling with timezone/cutoff. Do not relabel retrieval time
as source as-of.

The top-k section says tie boundaries and every Spearman x top-k disposition are declared, but does
not actually declare them. It gives no include/exclude-all-ties rule, no load-bearing overlap
thresholds for k=24/50/100, and no complete combination table. “More conservative governs” is not
executable until each metric has a closed disposition mapping.

V4 must either:

- make original-membership top-k descriptive only and let the frozen Spearman rule govern; or
- specify set construction at tied boundaries, denominators when the set exceeds k, missing rows,
  numeric overlap bands for each load-bearing k, and the complete cross-metric decision table.

Also state that the baseline hash serializes **ordered positional tuples**, not mappings; both are
plausible `json.dumps(rows, ...)` implementations and produce different hashes.

## Rulings carried forward

- **Ruling A:** unchanged and accepted. Current 328 identity / 285 matched fails; only an unseen
  future aligned vintage may use the prospective gates.
- **Ruling B:** implemented and accepted. The old comparison is permanently non-load-bearing.
- **Ruling R3:** accepted. Dominance is operational/source-fitness only, not redundancy proof.
- **Retention:** full census remains scratch-only; the corrected minimized artifact may be durable
  after findings 1–2 are repaired.

## Required v4 before round 4

1. Make generator input pins fail-closed and full-mode retention metadata/path handling safe.
2. Apply the exact minimization ruling in finding 2.
3. Narrow the position conclusion.
4. Correct retrieval-vs-as-of terminology and make top-k descriptive or fully executable.
5. Correct the scope/commit-status wording.

The framing remains stopped at failed horizon and cohort gates. No RED, build, or comparison opens.
H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
