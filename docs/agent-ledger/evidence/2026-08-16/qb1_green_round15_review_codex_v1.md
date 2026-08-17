# QB-1 GREEN Round 15 Independent Review — Codex v1

Date: 2026-08-16 ET  
Verdict: **NOT CLEAR** for registered execution  
Run: `f8f7551c-a145-46e2-b9b4-dec427f313ba`  
Round: `green-review` 15

## Pins and scope

- Claude request SHA-256:
  `dac2d776fad4c8d80c491d9b862227f1f4aeb52cc6b39033111d76f1f01a1096`.
- Adapter SHA-256:
  `021be2073d6d9609d2b0c2cf376c82d792df2c287e13cf0e262a67cdde3dbe44`.
- Execution seam SHA-256:
  `12df03a0258c62f375675cfa7b068ba4564db83e2474da29959ef1537831e3e8`.
- Correction-contract SHA-256:
  `a75dbc64b1d90a5d2d505963ad8a8a50990c7834259cbfc30e497c9f14f74d17`.
- Wall-census script SHA-256:
  `e02ca9b61da83d0ea4dc8d9323e629a23a686e4c9fccd1885065ca3b1a0dce7d`.
- Diff from the script-owned Round-15 open snapshot
  `bae7112c4e2c397162417544cd47703993906915ebc0ba27873776c090b1e769`
  is exactly the three authorized product/contract files. The registration,
  pinned input artifacts, publication gate, and matrix builder are untouched.

## Implementation checks that pass

1. **One parse implementation:** the adapter exposes
   `parse_validation_pbp`; normal ingestion delegates to it, and admitted
   snapshot read-back delegates to the same function. The registered
   `VALIDATION_PARSED_RENAMES["pbp"]` table remains the only rename authority.
2. **Correct ordering:** after the provisional review finding was accepted,
   the seam parses the defensively loaded PBP frame after receipt admission
   and before `load_validation_sources`. The source gate therefore receives
   `offense_team`, no `posteam`, and REG-only rows. There is no conditional
   already-parsed bypass.
3. **Fail-closed behavior:** missing `season_type`/`posteam`, reparsing an
   already-parsed frame, and a zero-REG result refuse by name. Raw bytes and
   receipt/provenance state remain unchanged; non-PBP frames are not parsed.
4. **Independent tests:** the five-file comparable bundle passed **696/696**
   in 51.84 seconds. The request's **695** count is stale by one after the
   late gate-spy contract; this is reconciliation drift, not a product-code
   failure. Claude's unpiped full suite reports **6,143 passed / 15 failed /
   12 skipped**, with the 15 named as the standing untracked cadence RED.
5. **Static checks:** Ruff passes all three scoped files; strict Python
   compilation and `git diff --check` pass. The evidence-only census script
   has one Ruff `I001` import-order violation, so the request's unqualified
   “Ruff ... clean” statement is too broad.
6. **Real-surface evidence:** the authorized census records zero pinned-column
   walls across all seven admitted datasets and 508,914 parsed REG PBP rows.
   Its full-composition probe then refuses before completion with
   `stat_value_invalid: weekly row [1026]: unusable identity player_id=nan
   season=2015`. No registered result was completed, read, or persisted.

## Blocking findings

### R15-G1 — the composition is still not executable

`build_study_matrix` applies `_validated_weekly_row` to the untouched weekly
pool before its all-position aggregation. That validator refuses the same
measured 192 provider placeholders already classified at the label boundary:
missing `player_id`, missing `position`, and exact validated zero across all
17 D2 inputs. Therefore a fresh registered rerun at these pins is known to
fail closed before producing a result. The PBP repair is correct, but it is
not sufficient for execution CLEAR.

### R15-G2 — the wall census does not establish “every remaining wall”

The diagnostic says explicitly that the full composition runs once and
records its **first** named refusal. Once the matrix refuses, no later stage is
reached. It supports “one observed next wall”; it cannot support the request's
“ONE remaining wall” claim or enumerate later named walls. The durable route
must correct that claim. Any further sweep must remain read-only and must
state which stages were independently exercised and which remain unreachable
behind an earlier fail-closed boundary.

## Registration read — matrix placeholder boundary

Classification: **implementation, not registration amendment**, but a fresh
bounded implementation word is required because Round 14 deliberately scoped
the predicate to label-builder records only.

- Registration §3 defines the target and qualifying game per player.
- Registration §4 defines a QB cohort with identity and prior history.
- Registration §5 requires `rush_td_share` team totals from the **all-position
  pre-QB-filter aggregation**. The exact placeholder class has no player id,
  no position, and validated zero in every one of the 17 ruled D2 inputs;
  specifically, its `rushing_tds` contribution to that all-position team
  denominator is exactly zero. It is neither a player observation nor a
  stat-bearing team contribution.

The smallest conforming boundary is:

1. Keep receipt admission, parsed-frame gates, pinned input frames, and the
   pool passed to `build_study_matrix` unchanged.
2. On the matrix's defensive weekly records only, immediately before
   `_validated_weekly_row`, exclude exactly the already-ruled conjunction:
   missing `player_id` **AND** missing `position` **AND** validated exact zero
   across all 17 D2 inputs; names remain audit evidence only.
3. Use one shared classifier for label and matrix consumers so the predicate
   cannot drift. Preserve fail-closed refusal for every near miss, including
   any missing-id row with a position, absent/malformed/non-finite/unproven
   cell, or any nonzero input.
4. Prove the full admitted frame and receipt digests remain unchanged, the
   all-position team-rushing totals are byte/value-identical before and after
   classification, all 192 exact placeholders are excluded at the defensive
   matrix-record seam, and every 1:1 near-miss mutant still refuses.

This boundary does not establish H2 and does not change a registered value.
H2 QB rushing remains **UNDER TEST**.

## Verdict and execution authority

**NOT CLEAR.** The already-granted fresh rerun is not fired and remains
unconsumed. There is no commit, push, merge, input mutation, publication, or
registered readout. The next action is David's word on the bounded matrix
implementation boundary above, followed by independent review; execution may
occur only on a later explicit CLEAR.
