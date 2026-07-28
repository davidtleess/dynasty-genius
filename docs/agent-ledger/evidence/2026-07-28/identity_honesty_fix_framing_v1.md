# TW28-IDENTITY-4 — Framing: the identity honesty fix + crosswalk preservation

**Author:** Claude Code (implementing lane) · **Status:** framing artifact, pre-RED.
**Authority:** David's word to Tower at 10:56 ET — *"ship the honesty fix and commit the file."*
**Codex adversarial challenge + my written disposition are required before any RED opens** (02
§Strategy/UX framing first). No code has been written. Nothing is committed.

**One unit is BLOCKED on a scope answer and is not framed for implementation below — Unit C.** Per
Tower's instruction to challenge scope before acting rather than after, the challenge is §3.

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

**Unit C — the false on-screen reason. BLOCKED, see §3.**

## 3. The scope challenge — Unit C cannot be done as worded

David's word, as Tower relayed it, is that *"the two affected rows must stop reading 'No active model
score for this player category.'"* Read literally, that is row-targeted, and row-targeting is not
reachable inside the authorised scope. Measured:

| | Identifiers actually present |
| :-- | :-- |
| The orphan crosswalk entry | `gsis_id`, `pff_id`, `pfr_id`, `espn_id`, `rotowire_id`, name, position, birthdate |
| The corresponding live PVO row | `sleeper_id` only — `identity_ids` reads `{espn_id: null, gsis_id: null, pff_id: null, pfr_id: null, sleeper_id: "13151"}` |

**The intersection of identifiers is empty.** The only shared field is the name. So marking exactly
those two rows requires either (i) matching on name — the failure mode the identity contract bans
outright — or (ii) enriching the materialized snapshot with the Sleeper payload's gsis, which is
`sleeper_universe.py:235-250` and is I-5 bridge work that David did **not** authorise and that
Codex's split explicitly holds back. Tower's instruction was to stop and say so rather than blend
them. I am saying so.

Two routes remain. I am not choosing between them; the choice is David's because both change what he
reads:

**Route 1 — class-level honesty (separable, no bridge work).** Stop the message asserting a cause the
system cannot verify. `app/api/routes/players.py:285-291` emits the category explanation for *every*
row lacking a model — roughly 11,600 of them — so the string is a blanket claim about a population
whose members have different reasons. Route 1 replaces it with what is actually known ("not in the
current modeled population") and says nothing about why. This removes the false attribution for the
two players *and* for every other row it was equally unearned on, and it touches no identity code.
Cost: David loses a specific-sounding reason he currently gets, in exchange for it being true.

**Route 2 — row-level honesty (requires I-5 first).** Enrich the snapshot deterministically so an
identity-miss row can be labelled as such, then give those rows a specific caveat. Strictly better
outcome, but it is bridge work and is not in David's word.

**My read, stated separately so the framing stays unanchored for Codex:** Route 1 is the honest fix
that fits the authorisation; Route 2 is the right eventual destination and belongs with I-5.

## 4. Mislead / nudge risks

- Route 1's replacement string must not imply the player is *bad* or *ineligible* — absence of a
  model is not a judgement. It must read as a system-state fact, not a player verdict.
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
7. Route 1: a row that legitimately has no model for a category-shaped reason still gets an accurate
   message; no row anywhere gets a cause the system cannot substantiate.
8. Route 1: the string is asserted by a test against the rendered surface, not only the API payload —
   the v1 board's mistake was checking the payload and missing what the card displays.
9. Unit D: the committed payload's sha256 equals the frozen hash, and the loader still resolves it at
   the same path the production constant names.
10. Unit D: nothing in the committed record asserts an upstream revision.

## 6. Overclaim check against the No-Verdict Line

Every unit is descriptive. Unit A withholds output rather than producing a confident wrong one, which
is the line's own remedy for untrustworthy inputs. Unit B reports counts and identifiers with no
ordering or emphasis. Unit C (either route) *removes* an unearned claim. Unit D adds provenance
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
