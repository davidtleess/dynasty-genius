# TW28-IDENTITY-11 — Codex adversarial review of framing v4 + split addendum

**Reviewer:** Codex, independent lane  
**Reviewed artifacts:**

- `identity_honesty_fix_framing_v4.md` — SHA-256
  `ecfb9891fa974e64b2e6e142c01fcc3b139f81413eacb06093f93d7128d1dc8b`
- `identity_honesty_fix_disposition_v3.md` — SHA-256
  `e34fe178c6c0b652c6b953deb5e61609e6652923bc9054f4e0141ae05bbc9f18`
- `identity_honesty_fix_split_addendum.md` — SHA-256
  `437d40bc7b2f834bbd4c38d30e2739da27b7146eb3c31a86c4492d71860aecee`

**Disposition:** **NOT CLEAR — six enumerated findings.** David's split remains
coherent: findings 1–4 belong to Thread 2 and do not gate the A/B/D GREEN.
Findings 5–6 correct the Thread-1 framing against the already-frozen Codex RED;
they do not select a partial-coverage threshold.

## What v4 fixed

The prior challenge's items 1, 2, 3, 4, and 7 are dispositioned correctly:

1. The 113 `MODEL_UNCERTAIN` rows are measured, named, unchanged, and escalated
   rather than absorbed.
2. `MARKET_ONLY` and `CONTEXT_ONLY` now appear in the declared route domain and
   an outside-domain route fails loud.
3. The position-absent branch no longer claims a causal relationship.
4. The branch-2 string no longer contradicts the lexical seed.
5. Unit D now carries a proven re-inclusion shape and binds to tracked bytes,
   not an invented upstream revision.

Prior items 5, 6, and 8 are not fully closed, for the reasons below.

## Fresh / residual findings

### 1. Branch 2 turns “unresolved” into “not a player”

Framing v4 §3.4 says every `UNRESOLVED_IDENTITY` row may assert **“This entry
isn't a player.”** That is not established by the route.

Production classification returns `UNRESOLVED_IDENTITY` whenever a player id is
present in the assembled universe but absent from the Sleeper player map
(`sleeper_universe.py:65-75`). The existing contract fixture proves the general
case with rostered id `"404"`: it is a roster player missing from the supplied
player map and is classified `UNRESOLVED_IDENTITY`
(`test_phase17_sleeper_universe_snapshot.py:33-41,58-69`). That may be a real
player whose identity failed to resolve.

The one live row happens to be pseudo-id `"0"` with no player fields. That
empirical fact cannot authorize a contract-wide “isn't a player” claim—the same
totality error v4 says it is correcting. Route 1 may state only that Dynasty
Genius cannot identify the entry, in manager prose without naming a route or
inventing a cause. Sentinel filtering remains separately unauthorized.

### 2. “Experimental” is another universal, unearned claim—not a harmless badge

V4 §3.5 explicitly preserves **“Experimental”** on all non-modeled branches.
Production sets `model_status="experimental"` for every non-modeled route
(`players.py:285-301`), and `PlayerDetailCard.tsx:35-40` renders the badge for
all of them.

That means an unresolved pseudo-entry, a retired/inactive non-player position,
a context-only kicker, and a market-only row are all labeled “Experimental.”
The route establishes no experiment. Replacing the false category explanation
while preserving this second false model-status claim does not achieve Unit C's
class-level honesty. V4 must either define the narrower rows for which
“Experimental” is earned or name/escalate this as another out-of-scope visible
defect. It cannot declare universal coexistence safe by framing.

### 3. “Whole viewport” still omits a live scaffolding violation

`PlayerInspector.tsx:96-100` visibly renders `player.sleeperId` directly beneath
the player label. PRODUCT.md's scaffolding-hide law bans raw database/source ids
in a user viewport. V4 §3.5 calls itself “what the whole viewport says,” but
does not mention this live identity/scaffolding defect.

This does not authorize silently removing the id inside Unit C. It requires the
same honest treatment as the 113-row finding: name it and establish whether it
is inside Route 1, or route it to David as separate scope. A composition claim
that ignores visible identity plumbing is not whole-viewport review.

### 4. The required composition artifact and visual gate are still incomplete

The design foundation requires, before code:

- the 5-second answer;
- focal hierarchy;
- desktop and mobile viewport sketches;
- lane-order statement.

V4 §3.5 pins statement count, placement outside the hero, and typography, but
does not provide those four required elements. Its sequence ends at a frontend
test/full-suite gate; it does not name the independent unanchored whole-viewport
visual audit, desktop + mobile + mandatory mid-scroll captures, or its scored
pass floor. Contract-green is explicitly not visual GREEN.

Because this changes visible status/explanation copy and removes two existing
labels across two surfaces, this is not a backend-only wording exercise. Thread
2 needs the complete pre-code composition artifact and the standing visual gate
in its sequence. Thread 1 remains backend-only and is unaffected.

### 5. The split addendum leaves a zero-board path open while claiming it closed

The addendum says the empty-board risk is closed by
missing/malformed/conflicting cases and that every orphan-bearing run otherwise
behaves as today. That is false at the zero boundary.

A structurally valid crosswalk can contain entries yet join **zero** Engine-B
predictions—for example, every prediction's GSIS is absent or every matching
entry has a null Sleeper id. The current producer then returns zero active PVOs
and publishes. Nothing is missing, malformed, or conflicting.

David's split rationale explicitly names “an app that publishes an empty board
with no error.” The frozen A/B/D RED therefore refuses:

- an empty prediction collection (`engine_b_predictions_empty`); and
- a nonempty prediction collection with zero successful joins
  (`engine_b_identity_join_zero_success`).

This does **not** choose the unresolved 1..502-of-503 policy. It isolates the
zero/nonzero boundary David named while leaving every positive partial-coverage
floor to him. Claude must either accept that boundary or challenge the RED with
file:line evidence before changing it; the addendum's current “risk closed”
sentence cannot stand.

### 6. A repeated prediction is not a crosswalk orphan

V4 seed 19 says a prediction-side `seen_sleepers` skip is “counted and named
like a crosswalk orphan,” while §5 separately promises duplicate counts and the
invariant `orphan_count == len(orphan_records)`. Those semantics still conflict.

For two parsed-equal predictions with the same GSIS, there is one player, one
successful join, one duplicate, and **zero orphans**. Calling the second copy an
orphan double-counts a player and corrupts the join denominator. For unequal
predictions with the same GSIS, silently choosing one is unsafe and the producer
must fail closed.

The frozen RED resolves this without imagination:

- equal repeat → `prediction_duplicate_count += 1`, score once, orphan count 0;
- conflicting repeat → `engine_b_prediction_conflict`;
- actual missing mapping / missing Sleeper id → deterministic orphan record.

The framing/addendum should adopt that separation. “Count and name every skipped
player” is the wrong abstraction for a duplicate row because no second player
exists.

## Checks performed

- Recomputed the three routed hashes before review.
- Read the full packet, disposition, v4, and split addendum rather than Tower's
  outline.
- Re-read PRODUCT.md and DESIGN.md and applied the `impeccable` product register.
- Inspected both rendered component stacks and the player-detail API branch.
- Traced `UNRESOLVED_IDENTITY` to its production classifier and existing real-id
  fixture.
- Recounted the local runtime artifact: 12,203 rows; routes 80 Engine A, 501
  Engine B, 2,141 inactive, 9,480 pre-model, 1 unresolved.
- Verified the live unresolved row is pseudo-id `"0"` while keeping the
  contract-wide distinction above.
- Re-read the frozen A/B/D RED and matrix: 18 fail / 1 preservation-control pass,
  zero-only refusal, no 1..502-of-503 floor.

No production script, refresh, frontend build, or model run was executed.
`decision_supported=False` is untouched. H2 QB rushing is unrelated and remains
**UNDER TEST**.

## Required disposition

Claude should answer all six:

- fix or explicitly escalate findings 1–4 in Thread 2;
- accept or evidence-challenge the zero-only boundary in finding 5 without
  selecting a positive partial-coverage threshold;
- align duplicate/orphan semantics with finding 6 and the frozen RED.

Thread 1 GREEN may continue independently. Thread 2 remains pre-RED until this
round is dispositioned and the complete composition artifact is frozen.
