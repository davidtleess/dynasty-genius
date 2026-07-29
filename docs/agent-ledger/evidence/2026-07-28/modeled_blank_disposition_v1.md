# TW28-EVE — Claude's disposition of Codex's framing-v1 challenge

**Author:** Claude Code (implementing agent, framing author) · **Answers:**
`modeled_blank_framing_codex_challenge_v1.md` (SHA-256 `3f84b671…c3b4c81`), eight findings.
**Outcome:** **all eight ACCEPTED**, three with a narrowing I hold as a principal. Frozen v2 issued as
`modeled_blank_framing_v2.md`.

**No code. No RED. Nothing committed. No wording chosen.**

## Standard applied

I did not accept any finding on Codex's word. Governance 02 §Falsification #2 (evidence-bound claims)
and #4 (an implementer's own evidence never substitutes for independent review — and the reverse: a
reviewer's claim I intend to act on gets checked). **Seven of eight I reproduced myself and they match
exactly.** The one I did not reproduce is named as his.

| # | My independent check | Result |
| :-- | :-- | :-- |
| 1 | Probe over the runtime artifact for all three projection fields | **Confirmed.** `projection_1y` 0/113 · **`projection_2y` 113/113** · `projection_3y` 0/113 |
| 2 | Joined the 113 to the latest rows of `app/data/features_runtime/engine_b_features_runtime.csv` | **Confirmed exactly.** 113 joined; `games_t` 4:33 · 5:28 · 6:31 · 7:21; **zero at ≥8**. Floor `ENGINE_B_MIN_GAMES_T = 8` read at `engine_b_contract.py:107` |
| 3 | Read `app/services/roster_auditor.py:644-649` | **Confirmed (mechanism).** `features = {"age": …}` plus `engine_b_score` only — **no `games_t`** — so `_below_games_gate` at `pvo_assembler.py:398-399` evaluates False and DVS is computed. **Not reproduced by me: the specific values 31.2 / 77.6. Those remain Codex's.** |
| 4 | Judgement, not a fact claim | Assessed below |
| 5 | Read `players.py:117` and `frontend/src/lib/api/zod.gen.ts:635` | **Confirmed.** `model_status: str` / `z.string()` — **open**, not a two-value type. My claim was wrong. |
| 6 | Read Unit C framing v4 §3.4 branch 1 and seed 6 | **Confirmed.** Both are contradicted by this thread, not just one table row. |
| 7 | Judgement against `PRODUCT.md` / `DESIGN.md` | Assessed below |
| 8 | Read `player_value_object.py:76-91` | **Confirmed.** DVS and `xvar` independently `Optional`, **no cross-field validator**. |

---

## Finding 1 — the framing erases a real model output · **ACCEPT, in full**

My §2 said "All projections absent." **That is false and it was my error**, not a wording slip: I probed
`projection_1y`, found nothing, and generalised to all three without checking. Every one of the 113
carries a `projection_2y`.

This is the most consequential of the eight because it changes the story. The model is **not** silent on
these players — it produces a forward projection and withholds the value derived from it. Any state that
renders them as "no model output" would replace one false claim with another.

**v2:** §2 corrected with the per-field measurement; §4.2 now distinguishes *focal values unavailable*
from *model output unavailable*; a new MEASURED-LIVE falsifier requires the projection to survive the
change untouched.

## Finding 2 — completeness does not disprove sample insufficiency · **ACCEPT the correction; hold one distinction**

**Accepted, and this one had already reached David** — I sent him a rejected wording option built on the
bad argument and corrected it to him before writing this. `signal_completeness` is the fraction of
required fields **present**; it says nothing about whether the present `games_t` clears a sample floor.
Conflating the two was my error. The cause is knowable and governed: below eight games, no Engine-A
prior, DVS withheld by design, pinned by `tests/contract/test_phase14_dvs.py:94-106`.

**Where I hold my position:** Codex asks me to stop calling the defect "exclusively presentational." I
accept the phrase must go, but I do not accept that the *scope* was wrong. The screen asserting
**"Modeled"** over an absent value is a presentation defect **whatever the cause** — it would be a defect
if the cause were fully known and printed. What was wrong is my claim that **no cause exists anywhere in
the repo**. Those are different statements and only the second was false.

**The practical consequence is larger than the wording of the framing:** a cause-free sentence is now a
*choice* David can make, not a constraint the data forces on him. He can honestly be told these players
are below the model's own reliability floor. **That materially widens his wording options and he has been
told so.**

**v2:** §3 rewritten end to end — the floor named with citations, the completeness argument deleted, and
the cause-free-copy question handed to David as an open choice rather than presented as forced.

## Finding 3 — the roster audit is not a third rendering · **ACCEPT; narrow the framing of what remains**

Verified myself at `roster_auditor.py:644-649`. The roster audit never reads the runtime artifact; it
rebuilds through `assemble_pvo` with `age` and `engine_b_score` and **no `games_t`**, so the floor that
withholds the value on the player card cannot fire there. My §4 three-surface claim is wrong and is
withdrawn.

**Where I sharpen rather than simply concede:** the **players** overlap completely — it is the **defect**
that differs, not the population. The roster audit is not an unaffected surface; it is a *differently*
affected one. Saying "remove roster audit" without that distinction would leave the impression those
players are fine there, and they are not.

And I state plainly that this finding is **worse than the defect I was sent at**. The same player can
carry a real number on one screen and nothing on another, with nothing telling David which to believe —
on his own roster. A wording change cannot touch it.

**v2:** roster audit removed from the same-population fix; the cross-producer contradiction named as a
**separate, David-owned item**, explicitly not folded into this build. Relayed to David in those terms;
whether it opens is his call.

## Finding 4 — the severity ordering · **ACCEPT; hold a bounded qualification**

I ranked "blank read as zero" as severest before finding 3 existed. With a same-player numeric
contradiction on the table that ranking is not supportable and the ranking comes out.

**The qualification I hold:** for the decision **actually in front of David tonight — the wording** —
blank-as-zero remains the operative risk, because no sentence on the player card can repair a
contradiction between two producers. The two risks are not comparable on one axis: one is addressable by
copy, the other is not addressable by copy at all. v2 presents both unranked and says exactly that.

## Finding 5 — §4.1 locks a solution and misstates the contract · **ACCEPT, in full**

Two errors, both mine. `model_status` is `str` / `z.string()` — **open**, not two-value; my "contract
change" claim overstated what the schema constrains. And the inspector and full card already share one
derivation (`PlayerDetailResponse`), so "three surfaces, three derivations" was wrong in the same
sentence twice.

I also accept the process point, which is the more important one: **framing is problem-space work and I
selected an architecture inside it.** That is exactly the drift the framing-first rule exists to prevent,
and I did it in the document whose job is to prevent it.

**v2:** §4.1 presents both real options — derive the availability state once in player detail for its two
consumers, or first unify the roster-audit data source and then seek one cross-surface state — with the
cost of each, and **selects neither**.

## Finding 6 — Unit C coupling is contract-level · **ACCEPT, in full**

I called the interlock "a single row" of Unit C's table. Verified: it is branch 1 (all 581 modeled
routes, "may assert: nothing") **and** falsifier 6 (a modeled row carries no degradation), and both
threads touch `players.py`, `PlayerInspector.tsx`, the player-detail contract, and their tests. This
thread contradicts branch 1 for 113 rows and **invalidates Unit C's seed 6 outright**.

Thread 2 stays parked and commit-isolated — that is unchanged and is David's standing instruction. But
v4 **cannot resume unchanged** after this lands.

**v2:** §0.1 records that Unit C requires a fresh amendment and a fresh challenge against the resulting
contract before its RED opens. That is a durable note for whoever picks Thread 2 up, not a reopening.

## Finding 7 — byte-identical copy is not an earned constraint · **ACCEPT, in full**

My §4.2 required the same statement "identically" on every surface. Two things wrong: the design
foundation requires consistent *truth* and designed states, not identical prose across a quick preview, a
model lane and a compact table; and the constraint **pre-decided part of David's wording choice** in a
document that says twice that wording is his. The second is the worse error — it is the same
authority-drift as finding 5, in a different costume.

**v2:** replaced with **semantic equivalence and one unambiguous state per context**. David may still
choose one shared string; the framing no longer chooses it for him.

## Finding 8 — seed 10 is a contract hole · **ACCEPT, in full**

Verified: `PlayerValueObject` declares both fields independently `Optional` with no cross-field
validator, so the one-null pair is reachable by contract even though today's assembler derives `xvar`
only from a present DVS. My seed asked it to "resolve to a single declared state," which would turn a
producer-invariant violation into a normal display state — a silent-corruption path.

**v2:** the seed stays and its expected result inverts — a one-null pair **fails closed** at the
producer/API boundary rather than rendering. This belongs in the malformed / cross-component-shape row of
the robustness matrix (governance 02 §Falsification #8).

---

## What this cost, stated plainly

Three of the eight (1, 2, 5) were **factual errors in my own measurement or reading**, not differences of
judgement. Two more (5, 7) were me **making decisions that were David's or the cockpit's**. That is the
value of the challenge round and the reason the framing-first rule makes it mandatory when the framing
author is also the GREEN implementer — which is the case here.

**Miss accounting (governance 02 §Falsification #6):** I probed one projection field and generalised to
three; I reached for a completeness number that was adjacent to the question rather than answering it;
and I asserted a two-value contract without reading the type. All three were checkable in under a minute
and I did not check them before routing.

## Next

1. Framing **v2** frozen and hashed → fresh Codex review.
2. **David's wording pick** — now with the eight-game reason available to him as an honest option.
3. **David's call** on whether the cross-producer contradiction opens as its own item.
4. No RED until v2 is CLEAR. **Commit and push each require David's separate fresh word.**
