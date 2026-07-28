# TW28-IDENTITY-4 — Codex adversarial challenge of current honesty-fix framing v2

**Reviewer:** Codex (independent technical reviewer)  
**Date:** 2026-07-28  
**Artifact reviewed:** `identity_honesty_fix_framing_v2.md`  
**Reviewed SHA-256:** `84dcf34a1dc840f773d4c2539ad59d5a191a7205141648d99f82f7056d233197`  
**Authority applied:** David's verbatim ruling, `"route 1"` — class-level honesty only.  
**Disposition:** **NOT CLEAR — the load-bearing live count is underinclusive and a
second rendered category claim is absent from the framing.**

This disposition supersedes
`identity_honesty_fix_framing_codex_challenge_v2.md`, which correctly challenged
earlier SHA `0492720690c2…` but cannot serve as the formal disposition for the current
in-place-revised bytes. The current revision removed the undefined “Unit E” label and
changed §6 from “either route” to Route 1; those two changes are credited below rather
than hidden.

No RED, implementation, production refresh, row targeting, name matching, I-5 bridge
work, sentinel population repair, or commit was opened.

## Enumerated challenge against Claude's five asks

1. **Ask (a), broken: the false-wording population is 3,453, not 2,233.**
   I independently queried the live 12,203-row runtime PVO. The blanket API message
   renders on 11,622 rows. There are **3,453** `PRE_MODEL` rows at modeled positions
   QB/RB/WR/TE:

   | Position | All statuses | Active-only subset |
   | :-- | --: | --: |
   | QB | 402 | 267 |
   | RB | 790 | 491 |
   | TE | 713 | 454 |
   | WR | 1,548 | 1,021 |
   | **Total** | **3,453** | **2,233** |

   The framing's predicate adds `sleeper_status == "Active"`, but player status is
   irrelevant to whether QB/RB/WR/TE are modeled categories. The omitted 1,220 rows
   are 1,137 Inactive, 81 Injured Reserve, 1 Physically Unable to Perform, and 1
   Practice Squad. Every one still has `engine_path=PRE_MODEL` and receives the same
   false category explanation. Correct every 2,233/9,389 reference and avoid the
   rhetorical `~1,100×` ratio.

2. **Ask (a), a second contradiction: “the real cause is absent Engine B features”
   is not true for the whole measured class.** The framing immediately says Kallerup
   and Williams are a subset of the 2,233, but both have Engine B feature rows; their
   failure is the crosswalk join. Route 1's virtue is precisely that the class-level
   message does **not** assert a cause. Delete the class-wide “real cause” sentence.

3. **Ask (b): the semantic contract is cause-free, but the proposed visible copy is
   not yet reviewable.** “Not in the current modeled population” does not identify
   features, identity, age, newness, or another cause, so it does not itself smuggle
   Route 2. But “modeled population” is system language, and the framing defers exact
   David-facing copy until commit. Pin candidate manager-prose strings and precedence
   before RED; implementation is too late to make the judgment-bearing copy decision.

4. **Ask (c): seed 13 is theatre if used as the contract.** A small banned-word list
   can reject an innocent sentence and still pass an implied or differently worded
   cause. Make the exact approved strings and branch mapping the primary assertions.
   A lexical scan can remain a supplementary scaffolding-hide guard, not proof of
   semantic honesty.

5. **Ask (d): no Route 2 smuggling was found in the proposed class keys.** Position,
   declared `engine_path`, and existing status are class fields; none targets the two
   identity misses or performs name matching. This part is CLEAR, provided copy does
   not infer why a particular `PRE_MODEL` row is absent. Row targeting, name matching,
   and I-5 remain unauthorized.

6. **Ask (e), missed production surface: `PlayerInspector` independently repeats the
   false category claim.** `PlayerDetailCard.tsx` renders the API degradation message,
   but `PlayerInspector.tsx:23-35` maps every non-modeled response to **“Unmodeled
   category” / “No active model score.”** A backend/full-card-only change leaves the
   same David-visible falsehood for all 3,453 modeled-position `PRE_MODEL` rows. Route
   1's rendered contract and RED must cover both current consumers of
   `PlayerDetailResponse`.

7. **Ask (e), synthetic case presented without classification.** The live PVO has
   **zero** `INACTIVE` rows at QB/RB/WR/TE. Seed 9 is useful prospective precedence
   coverage, but it is not a current overlap and must be labeled synthetic. The live
   category-copy negative control is the 6,027 `PRE_MODEL` rows outside QB/RB/WR/TE.

## Additional framing breaks

8. **The Route 1 mapping still is not total.** The current revision correctly removes
   the undefined “Unit E” label, but explicitly leaves the one
   `UNRESOLVED_IDENTITY` sentinel rendering today's false category copy. Class-level
   honesty does not require filtering or repairing that row. Give it a truthful
   fallback message keyed on its existing route, while leaving sentinel population
   repair out of scope. Also define precedence for `UNRESOLVED_IDENTITY`, `INACTIVE`,
   non-QB/RB/WR/TE, `PRE_MODEL` at a modeled position, null/unknown position, and
   healthy modeled routes. No raw route token may render.

9. **“Unusable crosswalk” and orphan output are underdefined.**
   `_load_ff_playerids` silently uses last-write-wins dict comprehensions for duplicate
   GSIS and Sleeper IDs; `_active_pvos_from_engine_b` silently drops repeated Sleeper
   mappings through `seen_sleepers`. Add prospective RED cases and explicit policy for
   non-object payloads, non-list `entries`, non-object rows, missing/wrong-type IDs,
   duplicate GSIS, duplicate Sleeper ID, conflicting mappings, and identical
   duplicates. Define deterministic orphan ordering and
   `orphan_count == len(orphan_records)`.

10. **The near-total join boundary is unspecified.** Seed 3 allows one orphan while
    seed 5 aborts at all 503. State what happens at 502/503 and the exact invariant
    that makes a crosswalk usable. Do not introduce an implicit coverage threshold.

11. **Unit D does not yet prove that the committed bytes become the production
    dependency.** The exact 3,768,182-byte payload is currently excluded by
    `.gitignore:122`, absent from `git ls-files`, and read through a constant pointing
    to that ignored path. Require one end-to-end RED invariant: the loader-resolved
    path is tracked, exists in a clean-checkout-equivalent state, and hashes to
    `8ed4b67578d06a24527356f9f355ed97f12be827e34885270c0b1d28c079f593`.
    This pins bytes only and must not claim missing upstream-revision provenance.

12. **The abort truth surface and sequence still need correction.** The scheduled job
    supplies `--report-path` with
    `app/data/model_capture/pvo_refresh_latest_report.json`; that registered report
    must say `status=aborted`, name the failed stage, and name the reason while the
    previous runtime payload and ready marker remain untouched. “Status marker” is too
    vague. The current revision correctly narrowed §6 to Route 1, but §7 step 2 still
    waits for David's already-issued route answer. Record the ruling as complete.

## Independent-check accounting

- **Independently reproduced:** 12,203 total rows; 11,622 blanket-message rows; route
  counts 9,480 / 2,141 / 1; 3,453 all-status modeled-position `PRE_MODEL` rows; the
  2,233 Active-only subset and its position split; all five omitted-status counts;
  6,027 `PRE_MODEL` non-modeled-position rows; zero current INACTIVE/modeled-position
  overlaps; the sentinel row; the second rendered category claim; silent duplicate
  overwrite/skip code paths; ignored/untracked crosswalk path; exact crosswalk hash;
  and the registered refresh-report path.
- **Code-read, not executed:** missing/malformed crosswalk abort mechanics and refresh
  failure publication behavior. No production script was run.
- **Taken on Claude's word:** none of the load-bearing measurements.

## Required v3

A reviewable v3 must answer all twelve items, correct the all-status measurement,
cover both rendered surfaces, make Route 1 total with candidate manager-prose copy and
precedence, distinguish live facts from synthetic robustness cases, define
crosswalk/orphan/join-boundary behavior, prove the tracked loader dependency, and name
the registered abort report.

This challenge does not authorize Route 2, row targeting, name matching, I-5, sentinel
population repair, Compliance Audit work, or DG2-S0-01 unit (d).
