# TW28-IDENTITY-4 — Codex adversarial challenge of honesty-fix framing v2

**Reviewer:** Codex (independent technical reviewer)  
**Date:** 2026-07-28  
**Artifact reviewed:** `identity_honesty_fix_framing_v2.md`  
**Reviewed SHA-256:** `0492720690c28100c76319ef8ae9a97787c56acdf15b2d49563d21795759e2b8`  
**Authority applied:** David's verbatim ruling, `"route 1"` — class-level honesty only.  
**Disposition:** **NOT CLEAR — the Route 1 framing still contains a broken live
measurement and misses a second rendered surface.**

No RED, implementation, production refresh, row targeting, name matching, I-5 bridge
work, or commit was opened.

## Enumerated challenge

1. **The headline false-wording count is wrong: 3,453, not 2,233.**
   I queried the live 12,203-row runtime PVO by `engine_path`, position, and
   `player.sleeper_status`. The blanket API message renders on 11,622 rows. There are
   **3,453** `PRE_MODEL` rows at modeled positions QB/RB/WR/TE:

   | Position | All statuses | Active-only subset |
   | :-- | --: | --: |
   | QB | 402 | 267 |
   | RB | 790 | 491 |
   | TE | 713 | 454 |
   | WR | 1,548 | 1,021 |
   | **Total** | **3,453** | **2,233** |

   The framing reproduced only the Active subset. The omitted 1,220 rows are 1,137
   Inactive, 81 Injured Reserve, 1 Physically Unable to Perform, and 1 Practice
   Squad. They still carry `engine_path=PRE_MODEL`; the API still tells them their
   QB/RB/WR/TE category has no model, which is false. Correct §3.2, §3.3 branch 3,
   the claimed 9,389/2,233 split, and the payoff language. Prefer the measured counts
   over the rhetorical `~1,100×` ratio.

2. **The framing misses a second David-visible false category claim.**
   `PlayerDetailCard.tsx` renders the API degradation message, but
   `PlayerInspector.tsx:23-35` independently reduces every non-modeled API response to
   **“Unmodeled category” / “No active model score.”** Fixing only
   `players.py` plus `PlayerDetailCard` leaves the same category falsehood in the
   inspector for all 3,453 modeled-position `PRE_MODEL` rows. Seed 11's
   rendered-surface assertion must cover both current consumers of
   `PlayerDetailResponse`, not just the full card.

3. **Route 1 is not total because “Unit E” does not exist.**
   The one `UNRESOLVED_IDENTITY` sentinel is inside the current 11,622-message
   population. Section 3.3 says it is “Unit E's problem,” but the authorized units are
   A/B/C/D and no Unit E is defined or authorized. Route 1 needs a truthful,
   class-level fallback for that current row, or the framing must explicitly leave
   the existing false copy in place and say why. It may not assume future sentinel
   filtering, row targeting, name matching, or I-5.

4. **Branch precedence and copy are deferred past the framing gate.**
   Section 3.3 names semantic branches but says the exact David-facing copy “belongs
   to him at commit.” That leaves the judgment-bearing behavior undecided until after
   RED/GREEN. Pin candidate manager-prose strings and exact precedence in the framing,
   then test them. The precedence must cover at least:
   `UNRESOLVED_IDENTITY`; `INACTIVE`; non-QB/RB/WR/TE; `PRE_MODEL` at a modeled
   position; null/unknown position; and healthy modeled routes. No raw route token may
   render. This is required by the ratified scaffolding-hide law and designed-state
   requirement, not visual embellishment.

5. **Falsification seed 9 describes a hypothetical overlap as if it were current.**
   The live PVO has **zero** `INACTIVE` rows at QB/RB/WR/TE. The precedence test is
   useful as a synthetic contract test, but it is imagination about production, not a
   measured current class. Label it explicitly as a prospective robustness case.
   Conversely, the current measured non-modeled-position `PRE_MODEL` population is
   6,027 rows and should be the live negative control for the category-specific copy.

6. **“Unusable crosswalk” is underdefined against current silent-overwrite behavior.**
   `_load_ff_playerids` uses last-write-wins dict comprehensions for duplicate GSIS and
   Sleeper IDs; `_active_pvos_from_engine_b` silently drops repeated Sleeper mappings
   through `seen_sleepers`. Add RED cases and an explicit policy for:
   non-object payloads; non-list `entries`; non-object rows; missing/wrong-type IDs;
   duplicate GSIS; duplicate Sleeper ID; conflicting mappings; and identical
   duplicates. Also define deterministic orphan ordering and the invariant
   `orphan_count == len(orphan_records)`. These are prospective robustness cases,
   clearly distinct from today's measured two orphans.

7. **The near-total join boundary is unspecified.**
   Seed 3 says one unjoinable prediction publishes with a report; seed 5 says all 503
   abort. The framing never says what happens for 502 of 503, or what makes the
   crosswalk “unusable.” State the exact publication invariant. A hidden or arbitrary
   coverage threshold would be new policy; if the intended rule is simply “at least
   one Engine B join plus complete orphan accounting,” say so and test the boundary.

8. **Unit D does not yet prove the committed bytes become the production dependency.**
   The exact payload is currently gitignored by
   `.gitignore:122` and absent from `git ls-files`; the loader constant points to that
   ignored path. A RED that merely hashes “the committed payload” and separately says
   the loader resolves “the same path” can pass without proving that a clean clone
   contains the exact load-bearing file. Require one end-to-end invariant:
   the loader's resolved path is tracked, exists in a clean-checkout-equivalent state,
   and hashes to
   `8ed4b67578d06a24527356f9f355ed97f12be827e34885270c0b1d28c079f593`.
   This pins bytes only; it must not claim the missing upstream revision provenance.

9. **The abort truth surface needs its real name.**
   A refresh failure leaves the prior runtime payload and ready marker untouched; the
   scheduled job supplies `--report-path` with
   `app/data/model_capture/pvo_refresh_latest_report.json`, and that registered
   refresh report is where the abort reason is emitted. Replace vague “status marker”
   language with that governed path/contract and assert `status=aborted`, the failed
   stage, and the named reason. An unchanged ready marker is necessary but is not the
   explanation.

10. **Two stale scope statements contradict David's completed ruling.**
    Section 6 says “Unit C (either route),” and sequence step 2 still waits for David's
    route answer. Change both to Route 1 only and record the ruling as complete. Route
    2 may remain only as out-of-scope history. Row targeting, name matching, and I-5
    remain unauthorized.

## Required v3 framing correction

A reviewable v3 must:

1. replace the 2,233 false-population claim with the 3,453 all-status measurement;
2. include both `PlayerDetailCard` and `PlayerInspector` in Route 1's rendered contract;
3. make the Route 1 mapping total, with candidate manager-prose copy and precedence;
4. distinguish current live defects from synthetic robustness tests;
5. define “unusable,” duplicate/conflict behavior, orphan-output invariants, and the
   near-total join boundary;
6. prove the frozen bytes are the tracked path the production loader actually reads;
7. name the registered abort-report truth surface; and
8. remove the stale “either route” / waiting-for-route language.

This challenge does not authorize Route 2, row targeting, name matching, I-5, sentinel
population repair, Compliance Audit work, or DG2-S0-01 unit (d).
