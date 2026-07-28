# TW28-IDENTITY-4 — Framing: the identity honesty fix + crosswalk preservation

**Author:** Claude Code (implementing lane) · **Status:** framing artifact v2, pre-RED.
**Authority:** David to Tower at 10:56 ET — *"ship the honesty fix and commit the file."*
Unit C route: David to Tower, verbatim — *"route 1"*.
**Codex adversarial challenge + my written disposition are required before any RED opens** (02
§Strategy/UX framing first). No code has been written. Nothing is committed.

**v2 supersedes v1** (parked, never delivered to Codex, never reviewed). Two changes: Unit C is
unblocked on Route 1 and designed in §3.3; and **§3.2 corrects the scope premise with a measurement —
the false-wording population is 2,233 rows, not 2.** The correction raises the fix's value ~1,100×
and changes nothing about the chosen route. Raised before acting, per Tower's standing instruction.

---

## 1. The concrete situation this serves

David opens a player card. For two players — Nick Kallerup (TE, SEA) and Ke'Shawn Williams (WR, CIN)
— the card says *"No active model score for this player category."* The model in fact has feature
rows for both; they are missing only because their gsis number has no Sleeper id in a frozen
crosswalk file. The card states a cause, and the cause is wrong.

Separately, the file that join depends on is one gitignored 3.77 MB payload with no backup. If it
disappears, the next refresh publishes a universe with zero Engine B values, passes every exit check,
and surfaces only a non-blocking review prompt.

Neither is an accuracy problem. Both are honesty problems, which for this product is the worse kind.

## 2. The authorised units

**Unit A — fail closed on a missing or unusable crosswalk.** Today `_load_ff_playerids`
(`scripts/build_universe_pvo_batch.py:48-50`) returns `({}, {})` for a missing file and every Engine B
player is then skipped by the bare `continue` at lines 101-103. Publication proceeds. Unit A aborts
instead. Boundary: this is about *publication*, not about repairing identity.

**Unit B — count and name every skipped player.** Today the skip is unrecorded. Unit B emits, in the
coverage report, a count plus a per-player record for each prediction dropped at the crosswalk join,
keyed by the identifiers the orphan side actually has (gsis, name, position). Boundary: reporting
only; it attaches nothing to any PVO row.

**Unit D — preserve the crosswalk as a frozen hash-stamped snapshot.** Payload hash
`8ed4b67578d06a24527356f9f355ed97f12be827e34885270c0b1d28c079f593`, independently reproduced by me
and by Codex. The record must state plainly that **committing pins the bytes and not the provenance**:
the snapshot carries only `source`, `pull_timestamp`, and `count`, with no upstream commit SHA, so the
upstream revision behind today's values is not reconstructable and the commit must not imply
otherwise. This is the item my v2 board got wrong in the other direction (see v3 §I-4).

**Unit C — the false on-screen reason. UNBLOCKED on Route 1 only** (David, verbatim: *"route 1"*).
Design in §3. Row targeting, name matching, and I-5 bridge work remain unauthorised.

## 3. Unit C — Route 1, and a measured correction to the scope premise

### 3.1 Why row targeting was refused (retained for the record)

The word as first relayed was row-targeted — *"the two affected rows must stop reading …"*. Measured:

| | Identifiers actually present |
| :-- | :-- |
| The orphan crosswalk entry | `gsis_id`, `pff_id`, `pfr_id`, `espn_id`, `rotowire_id`, name, position, birthdate |
| The corresponding live PVO row | `sleeper_id` only — `identity_ids` reads `{espn_id: null, gsis_id: null, pff_id: null, pfr_id: null, sleeper_id: "13151"}` |

**The intersection of identifiers is empty**; the only shared field is the name. Row targeting
therefore requires either name matching (banned by the identity contract) or snapshot enrichment at
`sleeper_universe.py:235-250` (Codex's I-5, unauthorised). David chose Route 1 instead.

### 3.2 THE SCOPE PREMISE IS WRONG, and wrong in David's favour

Tower's Route-1 scope states the replacement must be true *"for every row it appears on, including the
~11,598 where the current wording is accurate and the 2 where it is false."* **Measured on the live
runtime PVO, that 11,598 / 2 split is false.**

The message renders on **11,622** rows (`engine_path` not in `{ENGINE_A, ENGINE_B, BLEND_AB}`:
PRE_MODEL 9,480 · INACTIVE 2,141 · UNRESOLVED_IDENTITY 1). Of those, **2,233 are at a modeled
position AND carry Sleeper status `Active`**:

| Position | Rows told their *category* has no model, while that category IS modeled |
| :-- | :-- |
| WR | 1,021 |
| RB | 491 |
| TE | 454 |
| QB | 267 |
| **Total** | **2,233** (all `PRE_MODEL`) |

Named examples: Jake Haener (QB), Eric Gray (RB), Will Mallory (TE), Ronnie Bell (WR). Dynasty Genius
models exactly QB/RB/WR/TE, so for these 2,233 the stated cause — *player category* — is simply
untrue; the real cause is absent Engine B features. **The two identity misses are a subset of this
group, not a separate case.**

The honest split is therefore **≈9,389 arguably-accurate** (non-modeled positions — LB 1,162, CB
1,031, DB 858, DE 689, DT 645, OL 607, G 428, DL 302 — plus inactive rows) **and 2,233 false.**

**Consequence for the decision, stated plainly:** Route 1 is not "change a string on 11,600 rows to
fix 2." It corrects a false explanation on **2,233 rows**, of which 2 are the identity misses. The
payoff is ~1,100× what the authorisation assumed. Nothing about the chosen route changes; its value
does.

### 3.3 Route 1 design — true *and* specific, keyed only on fields already present

Tower's constraint is "true-and-specific, not a shrug," and specificity is reachable without any row
targeting, because the branch already reads `valuation.engine_path` (`players.py:249`) and the row
already carries position and Sleeper status. Three branches, each true for every row it covers:

1. **Position outside the modeled set** (~non-QB/RB/WR/TE) → state the real, category-level fact:
   Dynasty Genius models QB, RB, WR and TE. This is the one population where a category explanation
   is earned.
2. **`INACTIVE` route** → state the status fact, not a category one.
3. **`PRE_MODEL` at a modeled position** (the 2,233, including the 2 identity misses) → state that the
   player is not in the current modeled population, and **assert nothing about why**. This is exactly
   the boundary: it is true for a rookie awaiting features and true for an identity miss, and it
   claims neither.

`UNRESOLVED_IDENTITY` is the single `"0"` sentinel row. It is board item I-3, **not authorised by this
word**, so no copy is written for it here — it keeps whatever it renders today. Naming it as a fourth
branch would be scope creep dressed as completeness.

This is class-level by construction — the branch key is a declared engine route, never an inference
about which rows are identity misses. Exact wording is David-facing copy and belongs to him at
commit; the framing fixes the *contract* (what may be asserted per branch), not his prose.

**Route 2 remains unauthorised** — no row targeting, no name matching, no I-5.

## 4. Mislead / nudge risks

- Route 1's replacement strings must not imply the player is *bad* or *ineligible* — absence of a
  model is not a judgement. Each must read as a system-state fact, not a player verdict.
- **The `PRE_MODEL` branch must not become a promise.** "Not in the current modeled population" is a
  fact; "coming soon" or "awaiting coverage" implies a commitment the roadmap has not made, and would
  be a verdict-by-the-back-door about which players are worth modelling.
- **Specificity must not outrun the branch key.** The branch reads an engine route, so a message may
  assert only what the route establishes. Any wording that hints at *why* a `PRE_MODEL` row lacks
  features — features missing, identity unresolved, too new — is Route 2 smuggled in through copy, and
  is the single most likely way this unit fails review.
- Unit B's orphan record names players. Naming a player in an artifact must not read as flagging him
  as interesting; the record is about a join failure, not about the athlete.
- Unit D's commit message and any sidecar must not claim reproducibility of provenance it cannot
  deliver. "Hash-stamped" describes the bytes only.
- Unit A converts a silent success into a loud failure. A refresh that aborts must say *why* in its
  status marker, or we have moved the silence rather than removed it.

## 5. Candidate falsification seeds for the RED

1. Crosswalk file absent → publication aborts non-zero; no runtime artifact is written; no pointer or
   ready-marker advances; the status marker names the reason.
2. Crosswalk present but malformed / empty `entries` / valid JSON of the wrong shape → same abort
   path, distinct named reason. (Unit A must not key only on file existence.)
3. Crosswalk present, one prediction unjoinable → publication proceeds; exactly one orphan record;
   count is 1; the modeled population drops by exactly 1.
4. Zero orphans → the orphan block is present and empty, not absent (absence is indistinguishable
   from "not computed").
5. All 503 predictions unjoinable → abort, not a published universe with 503 orphan records.
6. Orphan record for an entry with no name → recorded with a named-unavailable field rather than
   dropped or fabricated.
7. Route 1, the load-bearing row: a `PRE_MODEL` row **at a modeled position** (one of the 2,233) must
   NOT receive a category explanation. This is the exact defect and the test that would have caught it.
8. Route 1: a `PRE_MODEL` row at a **non**-modeled position (LB/CB/OL/…) must still receive the
   category explanation — the fix must not over-correct the ~9,389 rows where it is earned.
9. Route 1: an `INACTIVE` row at a modeled position gets the status message, not the category one —
   the two conditions can co-occur and must not race.
10. Route 1: a modeled row (`ENGINE_A`/`ENGINE_B`/`BLEND_AB`) gets **no** degradation message at all;
    the change must not leak a message onto healthy rows.
11. Route 1: the message is asserted against the **rendered surface** (`PlayerDetailCard`), not only
    the API payload — checking the payload and missing what the card displays was the v1 board's own
    mistake, and Codex's ch.8 is what caught it.
12. Route 1: `GET /api/players/13151` and `/12971` — the two identity misses — must read the
    population wording with no stated cause, proving the boundary holds for exactly the rows that
    provoked the ticket.
13. Route 1 negative control: no branch's text contains a cause word (features, identity, unresolved,
    new, soon, pending) — a lexical assertion, so copy drift cannot silently reintroduce Route 2.
14. Unit D: the committed payload's sha256 equals the frozen hash, and the loader still resolves it at
    the same path the production constant names.
15. Unit D: nothing in the committed record asserts an upstream revision.

## 6. Overclaim check against the No-Verdict Line

Every unit is descriptive. Unit A withholds output rather than producing a confident wrong one, which
is the line's own remedy for untrustworthy inputs. Unit B reports counts and identifiers with no
ordering or emphasis. Unit C (Route 1) *removes* an unearned claim from 2,233 rows and keeps the earned one on ~9,389. Unit D adds provenance
honesty. No unit computes, emits, or renders a tier label, verdict, or recommendation, and
`decision_supported=False` is untouched throughout. No market data touches any model path. H2 QB
rushing is not involved and remains UNDER TEST.

## 7. Sequence I intend to follow

1. This framing → Codex adversarial challenge → my written disposition answering every item.
2. David's answer on the Unit C route (or Tower's confirmation that Route 1 is within his word).
3. Codex authors the RED over the seeds above; I implement GREEN; Codex reviews to an enumerated CLEAR.
4. Full-suite closeout tollgate before any commit.
5. Commit on David's word. **A push is a separate word** and is routed through Tower.

## 8. Explicitly out of scope

I-5 deterministic row attachment · the canonical-key decision (his ask 3, recommended parked) · the
failing Compliance Audit workflow · DG2-S0-01 unit (d) · any push. None were opened.
