# Footballguys `adp.csv` pilot framing v4 — Codex round-4 review

**Date:** 2026-08-09  
**Lane:** Codex, independent technical reviewer / prospective RED author  
**Framing reviewed:** `footballguys_adp_pilot_framing_claude_v4.md`  
**Framing SHA-256:** `c388ec90ccfe10c555ad6afb6980d91edea67cd6bd7c28c461aa9c20491e9831`  
**Generator reviewed:** `footballguys_identity_census_generator_v3.py`  
**Generator SHA-256:** `e0d35ee9f37c4e10eda46674cedeb28ac5d8408a09a919bdaa1d91cad5f1bf56`  
**Minimized census reviewed:** `footballguys_adp_identity_census_claude_v4_minimized.json`  
**Minimized census SHA-256:** `cca3025ad44654b57fa658b7c598060380b381aec2708f8353d703027f0005ce`  
**Disposition:** **NOT CLEAR.** The evidence and all four substantive v3 repairs reproduce, but
two fail-closed generator contracts and one decision-rule sentence remain defective. Horizon and
cohort gates remain failed; ingestion RED stays closed.

No provider contact, intake, durable raw store, model input, RED, commit, push, or new redundancy
comparison was performed by this lane. The submitted evidence generator was run only against the
pinned scratch inputs to validate its claimed outputs.

## Independent checks that passed

- All three submitted repo-artifact hashes and the minimized artifact's 11,337-byte size match.
- Default generation reproduced the minimized census byte-for-byte: 11,337 bytes, SHA-256
  `cca3025ad44654b57fa658b7c598060380b381aec2708f8353d703027f0005ce`.
- `--full` reproduced the submitted scratch-only output byte-for-byte: 271,352 bytes, SHA-256
  `f83e6d736ff40a4a9381df27eedaf4a4badf4980a7cea3da845b2ab9eb33bab5`.
- Both outputs reproduce the exact file-wide totals `364 same / 34 wrong / 155 unresolved / 55
  unverifiable` and SF totals `328 / 32 / 93 / 47`.
- The minimized artifact contains 34 wrong-human mappings without `sf_rank` or `consensus_rank`,
  aggregate top-window counts only, count+sorted-list-hash commitments for the 55 and 155 sets,
  repo-relative paths, accurate mode/retention text, and all four input/resolver/generator hashes.
- The position conclusion is now bounded to the evidence. Retrieval alignment is no longer called
  source-as-of equivalence, and the ordered-positional-tuple serialization recipe is explicit.
- Git reports all three submitted artifacts as untracked, matching the `nothing committed` claim.

## Findings

### 1. `_verify` has an active hash-mismatch bypass

Generator lines 47–52 do not implement the claimed rule "fail closed on any mismatch":

```python
if expected and not expected.startswith("6f3a1e1c") and actual != expected:
```

Any expected hash beginning `6f3a1e1c` accepts every actual hash. That prefix appears nowhere else
in the repository and is unexplained. I invoked `_verify` with a deliberately unequal actual value
and a synthetic 64-character expected hash beginning with that prefix; it returned normally and
printed `MISMATCH_ACCEPTED`.

The four present pins do not begin with that prefix, so the submitted census still reproduces. The
defect is nevertheless exactly a seed that passes current positive controls while violating the
declared general contract. Remove the exception. The predicate must be simply `actual != expected`
(and an absent/invalid expected pin must itself refuse, not disable verification). Add a direct
unit/positive-control call proving an arbitrary mismatch refuses, including the formerly exempt
prefix.

### 2. `--full` is labelled scratch-only but accepts every path outside the repository

Generator lines 176–179 reject only when `REPO in out.parents`. A Desktop path, another checkout,
a synced-drive path, or any other durable location outside this repository passes that condition.
This does not enforce the artifact's own `SCRATCH_ONLY_FULL_PROVIDER_DERIVATIVE` / "MUST NOT ... be
replicated offsite" contract or the round-3 requirement to refuse another durable root. The repo
negative control proves only one forbidden location.

Make full mode fail closed on destination too: positively allow only an explicitly recognized
scratch root (for example, resolved system-temp/private-temp roots or a separately declared and
validated scratch root), and reject everything else. Preserve the repo refusal test and add one
outside-repo durable-path refusal plus one valid scratch-path acceptance. Resolve paths before the
containment check so symlink or `..` spelling cannot evade it.

### 3. The top-k remedy retains a contradictory disagreement rule

Framing v4 lines 110–114 says original-membership top-k is descriptive only, carries no disposition
weight, and "the disposition rests on Spearman alone"—then retains "the more-conservative rule on
disagreement." With one load-bearing metric there is no cross-metric disagreement to resolve. The
clause is either dead machinery or silently leaves top-k load-bearing.

Delete the disagreement clause and state unambiguously that the frozen Spearman band alone governs
any future eligible comparison. If another metric is intended to disagree, name it and close its
mapping; descriptive top-k cannot fill that role.

## Ruling

**NOT CLEAR**, limited to findings 1–3. The submitted measurements and v3 dispositions otherwise
stand. Required v5 is mechanical:

1. remove the hash-prefix bypass and test arbitrary mismatches directly;
2. enforce a positive scratch-root allowlist for `--full`, with outside-repo durable refusal and
   scratch acceptance controls; and
3. remove the stale disagreement clause (or fully declare the other load-bearing metric).

The current decision state does not change: **horizon FAILED, cohort floor FAILED, ingestion RED
CLOSED, no comparison opened, nothing committed.** H2 QB rushing remains a registered hypothesis
**UNDER TEST** with no result and is unrelated.
