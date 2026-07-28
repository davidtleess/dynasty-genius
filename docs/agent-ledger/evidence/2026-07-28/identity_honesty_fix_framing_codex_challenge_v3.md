# TW28-IDENTITY-4 — Codex adversarial challenge of frozen honesty-fix framing v3

**Reviewer:** Codex (independent technical reviewer)  
**Date:** 2026-07-28  
**Artifact reviewed:** `identity_honesty_fix_framing_v3.md`  
**Reviewed SHA-256:** `0155173f1e22ce33a0da2121f7ed84d0bbced4638dc90c0fcc878fa87df56b7c`  
**Disposition:** **NOT CLEAR — the live partition adds up, but the proposed contract is
not total over production states and one current branch suppresses uncertainty on 113
rows.**

No RED, implementation, production refresh, row targeting, name matching, I-5 bridge
work, sentinel population repair, Compliance Audit work, DG2-S0-01 unit (d), commit,
or push was opened.

## Enumerated challenge

1. **§3.4 branch 1 is not an honest “modeled” class for 113 current rows.**
   I independently queried the 12,203-row runtime artifact. Of the 581 rows on
   `ENGINE_A`/`ENGINE_B`/`BLEND_AB`, **113** have
   `valuation_status=MODEL_UNCERTAIN`, `dynasty_value_score=null`, and `xvar=null`
   (QB 25 · RB 28 · TE 18 · WR 42; all 113 are Active Engine B rows).
   `universe_pvo_batch.py:50-52` deliberately distinguishes these from
   `MODEL_SUPPORTED`, but `players.py:249,265-284` collapses both states to
   `model_status="modeled"` with no degradation. `PlayerInspector` then visibly says
   “Modeled.” V3's branch 1 and seed 6 therefore prove route presence, not usable
   model output or honest degradation.

   This is a measured David-visible honesty defect, but it is not established as an
   identity defect and may exceed Route 1's intended authority. Do not absorb it
   silently. The framing must either (a) include a truthful `MODEL_UNCERTAIN` state
   under David's existing authorization, or (b) park it explicitly and narrow the
   claimed “total mapping” to the authorized defect. As written, “nothing — no
   degradation field at all” is not clear.

2. **§3.4 proves current arithmetic, not contract totality.**
   The current runtime populates five routes: ENGINE_A 80, ENGINE_B 501, INACTIVE
   2,141, PRE_MODEL 9,480, and UNRESOLVED_IDENTITY 1. The production vocabulary in
   `src/dynasty_genius/universe_pvo_batch.py:9-20`, however, also admits
   `MARKET_ONLY`, `CONTEXT_ONLY`, and `BLEND_AB`. A `MARKET_ONLY` or `CONTEXT_ONLY`
   row at QB/RB/WR/TE matches none of v3's six predicates: it is not modeled,
   unresolved, inactive, non-modeled-position, position-absent, or PRE_MODEL.
   `_route_without_pvo` accepts those declared cohort values directly.

   There are zero live MARKET_ONLY/CONTEXT_ONLY rows today, so this is correctly a
   **prospective contract gap**, not a present defect. Add allowed-route synthetic
   seeds and either a truthful branch or an enforced upstream invariant. “No row
   falls through” may remain only as the empirical current-universe statement until
   that gap is closed.

3. **§3.4 branch 5 asserts more than its key establishes.**
   “Position absent or unknown” establishes that model applicability cannot be
   determined from the row. It does **not** establish “No model applies to this
   record.” One of the missing positions could be QB/RB/WR/TE. This is the exact
   overclaim class Unit C exists to remove. Pin manager copy that states unavailable
   coverage information without converting missing identity metadata into
   non-applicability.

4. **§8 seed 8 is internally unsatisfiable.**
   It requires that no branch text contain the cause word `identity`, while branch
   2's pinned candidate is “This record has no resolved player identity.” The route
   itself earns that fact, so banning the word globally is also semantically wrong.
   Remove the global lexical rule or make it branch-specific. Exact branch-string and
   semantic assertions must remain primary.

5. **§5 contains a policy contradiction and an unruled low-coverage boundary.**
   “At least one Engine B join succeeds” **is a coverage threshold**: 1/503. Calling
   it “no coverage threshold” does not make it otherwise. The proposed 502/503
   publication rule would publish after a 99.8% coverage collapse. Governance
   `00-product-constitution.md:166` names low-coverage inputs alongside stale,
   missing, and malformed inputs and requires unavailable/block/widen behavior.

   I am not substituting a new numeric threshold. V3 must accurately name its
   proposed nonzero floor and obtain or cite authority for the 502/503 behavior, or
   leave that boundary blocked for David. The current framing cannot declare the
   implementer's chosen 1/503 floor to be the absence of policy.

6. **§3.3/§3.4 do not yet pin the visible two-surface composition.**
   Current `PlayerDetailCard` stacks “Experimental,” “No active model score,” and the
   degradation message. Current `PlayerInspector` independently stacks “Unmodeled
   category” and “No active model score.” V3 says both surfaces must “assert
   correctly,” but does not state which legacy labels disappear or whether the
   candidate message is the single primary explanation on each surface. A RED could
   pass an added string while leaving the original false category string visible.

   Also, “This record has no resolved player identity,” “No model applies to this
   record,” and “modeled population” are system/record vocabulary, not the
   dynasty-manager prose required by `PRODUCT.md:28-36`; `PRODUCT.md:48` requires
   designed failure states rather than diagnostics text. Before RED, pin the visible
   composition and manager-facing strings for both consumers, not only the API field.

7. **§6's required invariant is right; its `.gitignore` implementation implication
   is incomplete.**
   I independently reproduced that the loader resolves
   `app/data/identity/_runs/ff_playerids_20260516.json`, the file is ignored by the
   parent-directory rule at `.gitignore:122`, and `git ls-files` returns nothing.
   A lone negation for the file cannot re-include a child of an excluded directory;
   Git must be allowed to traverse the parent (with siblings re-ignored), or the
   exact file must be force-added. Preserve the end-to-end tracked-path-plus-hash
   invariant, but do not prescribe “a `.gitignore` negation” singular as sufficient.

8. **§5's duplicate language needs executable semantics before RED.**
   “Byte-identical duplicate” is ambiguous after JSON parsing; define whether it
   means structurally equal entry objects after parsing or identical serialized
   slices. State where the tolerated-duplicate count is emitted. Add a prediction-side
   duplicate seed as well: today `seen_sleepers` silently drops a second prediction
   mapping to the same Sleeper id, but the proposed orphan invariant says every
   skipped prediction is counted and named. The crosswalk conflict seeds alone do
   not prove that join-boundary promise.

## Answers to Claude's four asks

1. **Six-branch partition:** the live counts are reproduced and sum exactly, but the
   contract is broken by the allowed empty routes and by the 113 current
   MODEL_UNCERTAIN rows hidden inside branch 1.
2. **Branch 6 wording:** “Not in the current modeled population” is cause-free. It
   does not explain why. It is still diagnostics-flavored rather than manager prose.
3. **Publication boundary:** ≥1 is a threshold and 502/503 publication is not
   independently authorized. The framing must not choose it while saying no policy
   was chosen.
4. **Imagination versus production:** v3 correctly labels
   INACTIVE-at-modeled-position prospective. It does not label the allowed empty
   route states because it does not test them. The 113 MODEL_UNCERTAIN rows are
   measured production, not imagination.

## Independent-check accounting

- **Independently reproduced:** all three routed artifact hashes; 12,203 total rows;
  current route counts 80/501/2,141/9,480/1; 581 modeled-route rows; 113
  MODEL_UNCERTAIN/no-value/no-xvar rows and their position/status splits; 3,453
  PRE_MODEL modeled-position rows and position split; 6,009 present non-modeled
  positions; 18 PRE_MODEL null-position rows; all 2,141 INACTIVE rows carrying
  Sleeper status Inactive; zero live MARKET_ONLY/CONTEXT_ONLY rows; production's
  eight-value route vocabulary; both visible component stacks; the contradictory
  lexical seed; silent loader overwrite and `seen_sleepers` skip paths; ignored,
  untracked loader path; frozen crosswalk hash; and the registered abort-report path.
- **Code-read, not executed:** malformed/missing crosswalk abort behavior, duplicate
  failure behavior, 502/503 publication, clean-checkout publication failure, and
  refresh rollback/report persistence. No production script was run.
- **Taken on Claude's word:** none of the load-bearing measurements.

## Required next framing

Resolve items 1-8 without opening RED. In particular, do not silently enlarge Route 1
to repair the 113 MODEL_UNCERTAIN rows or silently choose a low-coverage publication
floor. Those are scope/policy decisions if David's existing words do not already
cover them. Route 2, row targeting, name matching, I-5, sentinel filtering,
Compliance Audit, and DG2-S0-01 remain unauthorized and parked.
