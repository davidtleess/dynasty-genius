# Wording options — the 113 players with no Dynasty Genius value

**For David. His choice; I do not pick.** Prepared 2026-07-28 evening on his word
*"do the framing and wording options tonight."* Design foundation (`PRODUCT.md` + `DESIGN.md`) read
before any of this was drafted.

**Nothing is built. Nothing is committed. Your pick unblocks the build.**

---

## What every option has to do

Three things, and they are in tension with each other:

1. **Say there is no number** — plainly enough that you never mistake a blank for a low rating. This is
   the sharpest risk: on Garrett Wilson's card, on your own roster, an empty space sits right next to a
   market price. Two of these players are yours and Jayden Daniels starts for another team in your league.
2. **Not say why** — because the system genuinely does not know. Its internal marker for these players
   is defined as *"no value came out"* and carries no reason at all. Any explanation would be invented on
   screen.
3. **Not read as a knock on the player** — absence of a model output is a fact about the model, never
   about the athlete.

The same wording has to work in three places: the **full player card**, the **quick preview panel**, and
a **roster table row**. Each option below is shown in all three.

---

## Option 1 — Plainest

> **Card:** No Dynasty Genius value for him.
> **Preview:** No Dynasty Genius value
> **Row:** `—` with a small chip reading **No value**

**For:** It is the same sentence the parked Unit C work proposes for other players with no value, so the
whole product would speak with one vocabulary instead of two. Shortest, calmest, hardest to misread as a
verdict.

**Against:** It makes these 113 sound identical to a player the model never looked at — and these are
different: the model did run on them. It also does nothing *active* to stop the blank-reads-as-zero
problem; it relies on you already knowing the difference.

---

## Option 2 — Says the quiet part out loud

> **Card:** No Dynasty Genius value for him. That's not a low value — it's no value at all.
> **Preview:** No value (not a low one)
> **Row:** `—` with a chip reading **No value**

**For:** This is the only option that directly attacks the thing most likely to mislead you. On the
31 players who *do* have a market price, the second sentence is doing real work.

**Against:** Two sentences where the rest of the product uses one, and the short forms get clumsy
("not a low one" in a narrow panel). Slightly defensive in tone — the surface protesting rather than
stating.

---

## Option 3 — Matches the words already on the card

> **Card:** Dynasty Genius value unavailable for him.
> **Preview:** Value unavailable
> **Row:** `—` with a chip reading **Unavailable**

**For:** Your player card already says *"Market unavailable"* and *"Model unavailable"* in other states.
This adds no new concept — it reuses a word you are already reading elsewhere on the same screen. Cheapest
to absorb.

**Against:** "Unavailable" quietly suggests *temporarily* unavailable — that it'll be back. We cannot
support that. It's a small promise about future coverage that nobody has made.

---

## Option 4 — Tells you what you actually lose

> **Card (the 31 with a market price):** No Dynasty Genius value for him — nothing to set against his
> market price.
> **Card (the other 82):** No Dynasty Genius value for him.
> **Preview:** No value to compare
> **Row:** `—` with a chip reading **No comparison**

**For:** It names the consequence that matters to a decision: for these players you cannot see the gap
between our number and the market's, which is the whole point of the product. Most useful to you
mid-trade.

**Against:** It only tells the truth for 31 of the 113 — the other 82 have no market price either, so the
clause would be wrong for them. That means two variants and a rule deciding between them: more moving
parts, more to get wrong, and two different sentences for what is really one situation.

---

## Rejected before it reaches you — and why

> ~~"Not enough data on him yet."~~

This is the phrasing that sounds most natural, so I want to be explicit that it is not on the table and
why. It fails twice, independently:

- **It is measurably false.** 53 of the 113 have *complete* model inputs and still produced no value. A
  shortage of data is not the explanation for the largest group among them.
- **"Yet" is a promise** that the model will get to him — which is both a claim about future work and,
  quietly, a judgement about which players are worth modelling.

If you want something in this spirit, tell me and I will find a version that doesn't assert a cause.

---

## Can they be combined?

Yes, and it is worth knowing before you pick. **Option 1's sentence plus Option 2's second clause, but
only where the blank actually sits beside a market number.** You would get one vocabulary across the
product and the anti-misreading protection exactly where the misreading can happen — at the cost of the
sentence being slightly different in two places.

## My honest read — yours to overrule

If you want the plainest thing that cannot be misread as a verdict, **Option 1**. If you want the surface
to actively defend against the blank-equals-zero misreading, **Option 2**. I would argue against
**Option 3** on the "unavailable implies temporary" point and against **Option 4** on the two-variants
complexity — but both are defensible and neither is a governance problem.

**Tell me the number (or the combination) and the build starts.**
