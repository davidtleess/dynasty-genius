# Footballguys redundancy measurement — Codex admissibility ruling

**Date:** 2026-08-09  
**Lane:** Codex, independent technical reviewer / prospective RED author  
**Pre-registration reviewed:** `footballguys_redundancy_preregistration_claude_v1.md`, SHA-256
`abf6fa6cdfb91efcf9bdc2d35c677372eb9ed4f6c166e39286cac8948e27a786`  
**Result reviewed:** `footballguys_redundancy_result_claude_v1.md`, SHA-256
`259e9832005b63dea3dc3e689c58a0c8524f8f0452cd7540ad5c4f15f4cfd618`  
**Overall assessment:** **NEEDS REVISION. The submitted statistic is not admissible for a
redundancy disposition. Preserve it as a disclosed exploratory observation, not a finding.**

No intake, store, provider contact, model input, surface, scheduler, RED, or landed implementation
was authorized or performed by this lane. This review parsed the known local bundle read-only and
queried the existing FantasyCalc database read-only. The bundle itself was not executed.

## 1. Chronology and process

The pre-registration hash matches the disclosed hash. Local metadata is consistent with the
reported order: pre-registration mtime `22:10:16 -0400`; result mtime `22:11:42 -0400`. A hash
binds content, not time, so this is corroboration rather than an external timestamp. I accept the
implementing lane's disclosed sequence; there is no basis to call this defiance of an instruction
that had not arrived or a threshold chosen after seeing the statistic.

The procedural defect is still material: the implementer ran the decisive measurement while the
independent framing review that owned its admissibility was open. More importantly, the hashed
document froze only threshold bands. It did not freeze a minimum verified-cohort floor, exact
identity/normalization rules and whitelist, complete attrition states, top-24 definition, raw and
baseline content hashes/settings identity, tie method, or an interpretable same-horizon construct.
It is therefore a partial threshold registration, not a complete analysis pre-registration.

## 2. Calculation and cohort replay

The submitted attrition table does not add to 500:

`35 + 47 + 2 + 38 + 285 = 407`.

It omits 93 `source_only` rows. That alone falsifies the claim that every exclusion was named.

An independent replay used:

- the pinned `adp.csv` bytes, SHA-256 `1f7afcbfdd7b9c6d08dc21a0017f05d4a30fa64e0cd580c6295c5a5fc3a57eb9`;
- production `IdentityIndex.from_governed_crosswalk()` against
  `ff_playerids_20260516.json`;
- `projections.csv` name evidence with the disclosed five source IDs for Gainwell, Okonkwo,
  Tinsley, Borregales, and Hibner treated as the bounded nickname whitelist; and
- FantasyCalc `fc_native`, `2026-08-09`, settings hash `e27351d720e9fcf0`.

The first replay admitted every hand-verified same-human nickname variant, as the identity addendum
classified them. That ladder is:

| State | n |
| :-- | --: |
| `adp_sleeper-sf` populated | 500 |
| production `source_only` | 93 |
| no `projections.csv` name evidence | 47 |
| verified wrong human | 32 |
| verified same human but no Sleeper ID | 3 |
| verified same human but absent from FC snapshot | 38 |
| retained | **287** |

The other two members of the file-wide 34 wrong-human census, Brock Wright and Davis Allen, have
no `adp_sleeper-sf` value. They cannot be counted as exclusions from the 500-row SF slice. Hibner
is one of the disclosed same-human variants but lacks a Sleeper ID, producing three rather than two
in that state.

After the initial ruling, Claude disclosed the missing run-time rule while constructing framing v2:
the run used exact normalized-name agreement and therefore excluded nickname variants even though
the identity addendum had hand-verified them as the same humans. With that additional rule, the
submitted result is exactly reproducible:

- the omitted 93 remain `source_only`;
- the submitted 35-name-exclusion cell consists of **32 wrong humans in the SF slice plus three
  verified same-human variants** (Gainwell, Okonkwo, and Hibner), not 34 wrong humans;
- only two other rows then remain in the no-Sleeper-ID state;
- `n=285`, Spearman `0.9669669841`, rounds to the submitted `0.9670`; and
- survivor-reranked top-24 overlap is 22/24.

This makes the calculation reconstructible **after disclosure**. It does not make the cohort rule
pre-registered: the registration did not say exact-name-only, did not pin the normalization or
whitelist treatment, and said the 34 measured wrong-human IDs and unverifiable rows were excluded.
The result artifact also mixed the file-wide 34 with the SF-slice 32. The 287-row
same-human-inclusive replay (`rho=0.9667`) is the appropriate sensitivity check; neither version
changes the admissibility ruling.

The submitted `22/24` is also definition-sensitive. It is reproduced by taking the top 24 **after
reranking the survivors**. If top-24 means original source membership (`rank <= 24`), only 16
verified/matched top-24 IDs survive on each side and their overlap is 14. The registration did not
choose between those estimands. Survivor-reranking must not be presented as ordinary source
top-24 overlap.

## 3. Rulings requested

### R1 — Is the rho measurement admissible at all?

**Only as an exploratory observation and audit-trail fact that the run occurred. The arithmetic is
reconstructible after the missing exclusion rule was disclosed; it is still not admissible as a
pre-registered redundancy result, a band classification, or decision evidence.**

Even a corrected current-vintage replay would answer only: *among a selected, established-player-
heavy 57.4% survivor cohort, the two orderings are highly associated.* It cannot establish
file-wide redundancy, cannot speak for the identity-failed young-player tail, and cannot compare
constructs until the exact Footballguys horizon is established.

### R2 — Is withdrawing the interpretation while retaining the number the right remedy?

**Yes, as the first remedy, but the existing result text must be explicitly superseded.** Retain
the submitted `0.9670 / n=285 / 22-of-24` as a provenance record labeled
`invalidated_for_decision=True` and `decision_supported=False`. Do not leave the opening
`REDUNDANT` band selection or the later sentence *"Redundancy is established for the verified
core"* standing as findings.

A corrected v2 may report the reconstructed `0.9670 / n=285` and the same-human-inclusive
sensitivity `0.9667 / n=287`, with a complete reconciled ladder and both top-k definitions. It still
may not select the registered band. Because this result is now known, the same vintage cannot be
made prospectively confirmatory by writing a better registration after the fact. If David
authorizes continued study, freeze the complete protocol and test it on a genuinely unseen future
Footballguys vintage / aligned FantasyCalc snapshot (or a genuinely unexamined holdout fixed before
access).

### R3 — Does the FantasyCalc dominance comparison stand independently?

**The measured operational comparison stands; the universal dominance conclusion does not.** The
existing FantasyCalc lane demonstrably carries value spacing and ties, 47 daily snapshots from
2026-06-24 through 2026-08-09, populated Sleeper IDs, a declared dynasty-trade construct, and an
already-operating acquisition path. The observed Footballguys artifact is one manual rank-only
bundle with unsafe PFR-like identity and an unresolved horizon. Those facts independently support
**no ingestion build now** and make FantasyCalc the superior incumbent for the already-defined
dynasty-market-price job.

They do not prove Footballguys is informationally dominated *on every axis that matters*. If the
exact field is dynasty-startup draft behavior, it is a different construct that a trade-price feed
does not automatically subsume. If it is seasonal redraft, the comparison is confounded in the
other direction. Until horizon and use case are fixed, the dominance table is a strong
source-quality/procurement argument, not a redundancy finding and not independent proof of zero
incremental information.

## 4. Disposition

The framing verdict remains **NOT CLEAR FOR RED OR INGESTION BUILD**. Pausing for David's priority
ruling is correct. No more current-vintage statistic should be promoted or interpreted. If David
stops the candidate, the defensible record is `blocked_for_use` because identity correctness and
horizon/use fitness are unestablished and a safer incumbent already exists—not because the
submitted rho proved redundancy.

H2 QB rushing remains a registered hypothesis **UNDER TEST** with no result and is unrelated.
