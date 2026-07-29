# TW28-EVE — Codex fresh review of modeled-blank framing v2

**Reviewer:** Codex (independent review lane)  
**Reviewed artifact:** `modeled_blank_framing_v2.md`  
**Reviewed SHA-256:** `a011587dd78b3045f19e2a44c92c59d6ee69d7bad2cfb55a897be3a776a4c584`  
**Disposition artifact checked:** `modeled_blank_disposition_v1.md` at
`403567d16ac6b5846a1fd0319142a2dd35f48b403c61ce9f1f58ce4ae07ea6c6`  
**Disposition:** **NOT CLEAR**

No wording is proposed. This review clears or challenges framing content only and
schedules no RED, build, commit, or push.

## What v2 correctly integrates

1. Projection measurements now match both independently probed vintages:
   runtime 113/113 and seed 114/114 have `projection_2y`; neither population
   has one-/three-year projections.
2. The eight-game conversion floor, sample distribution, and distinction
   between signal presence and sample adequacy are correctly folded.
3. Roster audit is removed from the same-population surface assertions.
4. The prior severity ranking is removed; blank ambiguity and cross-producer
   contradiction are separated.
5. The architecture is presented as candidates instead of a closed enum change.
6. Unit-C's contract-level conflict and required future re-challenge are explicit.
7. Byte identity is correctly replaced by semantic equivalence.
8. The one-null pair is no longer normalized into an ordinary display state.

## Fresh findings

### 1. “Modeled” is now proven true; the framing still calls it false

The central v2 correction is that every affected player has a real Engine-B
two-year projection (`modeled_blank_framing_v2.md:78-88`). That means the
surface's flat “Modeled” status is not false: the route is modeled and a model
output exists.

But v2 still says:

- “the surface asserts a state that is not true” (`:61-62`);
- the player-detail API is defective because it decides modeled status from the
  route (`:147-164`);
- “absence of a model output is a fact about the model” (`:234-235`).

Those statements contradict v2's own corrected evidence. The defect is narrower
and more precise: the surface uses one `modeled` state to carry two different
questions—whether a model ran, and whether focal DVS/xVAR are available—then
leaves the focal slots blank. The first answer is yes; the second is no.

The framing and RED seeds must preserve `model_status="modeled"` (unless David
separately changes that semantic contract) and add/derive focal-value
availability rather than relabeling a genuinely modeled player as unmodeled or
degraded. Sweep all stale “no model output” / false-modeled language.

### 2. Section 3.1 overrules an unreviewed policy and cites a partly false caveat

V2 says the withholding is “not a bug” and “honesty discipline working exactly
as designed” (`modeled_blank_framing_v2.md:112-119`), while §3.3 correctly says
the eight-game floor and projection/DVS pairing have not been investigated or
ruled here (`:133-137`). Intentional current behavior is established; correctness
is not.

There is also a concrete source caveat defect. In the no-Engine-A-prior branch,
the assembler sets `dynasty_value_score=None` and then appends:
“Engine A prospect score used as prior”
(`src/dynasty_genius/pvo_assembler.py:448-456`). No prior was used in that
branch. All 113 affected rows carry that sentence. Therefore v2 may use the code
and `games_t` probe to establish the current floor behavior, but it must not cite
the row caveat as an honest causal receipt.

Narrow §3.1 to “intentional and contract-tested current behavior, not changed
here,” and name the false-prior caveat as another separate producer-honesty item.
Do not rule the underlying policy correct before §3.3's investigation.

### 3. “The players overlap completely” is false for David's roster-audit surface

Roster Audit calls `get_my_roster()` and emits David's roster only
(`app/services/roster_auditor.py:614-623`;
`get_my_roster` returns only `my_roster["players"]` at `:436-462`).
The affected runtime population is 113; only two are on David's roster.

Thus `modeled_blank_framing_v2.md:186-200` mixes:

- two currently surface-relevant players: Braelon Allen and Garrett Wilson; and
- a mechanism-only reconstruction for Jayden Daniels, who is on roster 7 and
  does not appear on David's Roster Audit.

The cross-producer mechanism is real, and the exact Braelon/Garrett probes remain
valid independent evidence. The **populations do not overlap completely**.
State the current visible overlap as 2/113 and label Jayden as a mechanism probe,
not a current cross-surface example. The separate David-owned item remains
warranted.

### 4. Option A is still selected and scheduled despite the text saying otherwise

Section 4.2 says:

- Option A “ships tonight if David picks a wording” (`modeled_blank_framing_v2.md:171-173`);
- “Neither is selected here” (`:177`);
- immediately afterward, “(A) is the scope of the word David gave” (`:177`).

David's word authorized framing and wording options. “Perhaps we can build” is
appetite, not build authority; Tower stated that boundary explicitly. Wording
selection would not itself authorize RED or GREEN.

Describe A as the bounded candidate only. Remove “ships tonight” and the claim
that David already selected its build scope. Sequence §9 must add a fresh
David build/RED word before Codex authors RED. A reviewer CLEAR would clear
content only and schedule nothing.

### 5. Seed 11 does not name which fail-closed boundary owns the refusal

Seed 11 requires a one-null pair to fail closed “at the producer/API boundary”
(`modeled_blank_framing_v2.md:268-275`). That slash hides two materially
different scopes:

- **Player-detail API boundary:** refuse the malformed requested row without
  changing the PVO publication contract. This fits candidate A.
- **PVO producer/schema boundary:** add a cross-field invariant that can abort
  publication or reject PVO construction repo-wide. That is a broader
  model-contract change and is not authorized by this surface framing.

The current `PlayerValueObject` schema explicitly permits independent nullability;
the assembler's dependency is implementation behavior, not yet a ratified global
schema invariant. For candidate A, pin the RED to the player-detail API boundary
and require a typed refusal for the affected request. If David later chooses a
producer invariant, that belongs to the separate model-contract item with an
explicit publication/failure contract.

## Required next disposition

Please answer all five findings accept/reject with evidence, issue a frozen v3,
and request a fresh review. No RED opens from this review.

