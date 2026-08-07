# Layer 1 A-C steps 1-3 — round-5 recheck

**Reviewer:** Codex, independent reviewing lane  
**Layer:** Layer 1 inventory  
**Artifact:** `docs/layer-1-data-inventory-catalog.md`  
**Reviewed SHA-256:** `0d6a1ea4a20a4f7d0b3b5100ceda37b1d4981d841171797de24067483fa2ee00`  
**Verdict:** **NOT CLEAR — one current-state contradiction (U1).**

## Checks run

- Recomputed the artifact hash: exact match.
- Recomputed the catalog diff: 376 insertions / 91 deletions.
- `git diff --check`: clean.
- `scripts/validate_governance.py`: PASS.
- Re-read the complete §4.4 table rather than only the N11/N19 deltas: 35 grouped rows, every row
  uses one of the seven allowed automation classes, the declared member surface is present, and the
  corresponding §6E current/target classes are consistent.
- Rechecked T1's four live closure surfaces, T2's N19 source-clock/local-pull separation, and T3's
  live versus historical FantasyCalc counts.
- Independently remeasured `fc_forward_capture.db`: 20,518 raw, 20,518 joinable, 44 snapshot dates,
  through 2026-08-06.

## Accepted

T1-T3 are closed. The two §4.4 edits are correctly disclosed, N11=`blocked` and N19=`blocked` are
the right current classes, and N19's upstream clock is correctly `UNVERIFIED`. The fresh
**whole-table §4.4 review is CLEAR at this pin**; its superseded earlier pin is no longer being used.

## U1 — current canonical paragraph still asserts the pre-authoring state

At lines 495-498, §3.1 says Table B-N is **still owed** complete R7 states, final automation/job
edges, parallel-route dispositions, and a defensible PFF aggregation rule.

That is false in four directions:

1. §6D authors all five R7 states for the enumerated rows; they await review rather than authorship.
2. §§4.4/6C/6E author the automation/job/freshness edges; only the two source clocks N1-N8 and N19
   remain unmeasured.
3. §6B authors the parallel-route dispositions; they await review rather than definition.
4. §6A lines 862-864 explicitly removes PFF combined-view aggregation from the A-C blocking path
   and places it in later semantic-layer work.

The paragraph may continue to say the table is not checked off, but it must name the real gate:
independent review plus the two unmeasured source clocks. As written, it directly contradicts the
closure matrix and recreates T1 outside the sites swept in round 5.

## Boundary

No checkbox moves, implementation, capture, scheduler, consumer migration, commit, or push is
authorized by this review. H2 QB rushing remains a registered hypothesis **UNDER TEST** with no
result.
