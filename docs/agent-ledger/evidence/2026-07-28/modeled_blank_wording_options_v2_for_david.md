# Wording options v2 — re-cut against the eight-game reason

**For David. His choice; I do not pick.** Re-cut on his word, 20:33 — *"re-cut the wording."*
Supersedes `modeled_blank_wording_options_for_david.md` (v1), which he has already read. **v1's options
are not silently retired below — each is marked survives / weaker / dead, with the reason.**

**Nothing is built. Nothing is committed.**

---

## What changed since you read v1

I verified the reason these 113 players have no value, and it is uniform:

**All 113 have played 4–7 games. The model requires 8 before it will publish a value.**

| games played | 4 | 5 | 6 | 7 | 8 or more |
| :-- | --: | --: | --: | --: | --: |
| players | 33 | 28 | 31 | 21 | **0** |

The floor is a governed constant (`ENGINE_B_MIN_GAMES_T = 8`) and the model **deliberately** withholds the
value below it. This is the honesty discipline working correctly one layer down — and the screen then
misreporting it.

**Three things follow, and they change the menu:**

1. **A reason is now honest to say.** In v1 I told you no reason existed. That was my error.
2. **It needs no variants.** It is true of all 113 identically — no per-player rule, no two-case split.
   That is exactly the cost that made v1's Option 4 expensive.
3. **"Yet" is now defensible.** I ruled it out in v1 as a promise about the model's roadmap. It isn't —
   games accumulate. "Yet" is now a statement about this season, not a commitment about future coverage.
   **That reversal is mine and you should know I made it.**

**One thing I got wrong in the other direction, too:** the model is not blank on these players. **Every
one of the 113 has a two-year projection.** It has a forward number and withholds the *value* built from
it. So "came up empty" — v1's Option 4 framing — was never accurate.

---

## Where v1's four options now stand

| v1 option | Status | Why |
| :-- | :-- | :-- |
| **1 — "No Dynasty Genius value for him."** | **Survives, unchanged** | Still true, still plainest. But it is now a *choice to withhold an available reason*, not the most you could honestly say. You should pick it knowing that. |
| **2 — "…not a low value — no value at all."** | **Survives, narrower use** | Its second clause exists to stop the blank-reads-as-zero misreading. A stated reason does that job on its own. Option 2 is now most useful **only if you choose not to give the reason.** |
| **3 — "Value unavailable."** | **Survives — and my objection is withdrawn** | I argued against it because "unavailable" implies *temporary* and nothing supported that. **The eight-game floor supports it exactly.** These players are genuinely temporarily short. Option 3 got stronger, not weaker. |
| **4 — "nothing to set against his market price."** | **Dead** | It needed two variants (31 players with a price, 82 without). The reason below is uniform across all 113 and tells you more at lower cost. It is dominated on both axes. |

---

## The new options

### Option 5 — The reason, plainly

> **Card:** Not enough of this season on him yet — the model waits for eight games before it puts a value
> on a player.
> **Preview:** Under eight games — no value yet
> **Row:** `—` with a chip reading **Under 8 games**

**For:** Tells you the actual bar and that he hasn't cleared it. It cannot be misread as a low rating,
because it explains itself. Uniform across all 113 — no variants, no per-player rule. **Cheapest of the
reason-giving options: the number 8 is a constant, so nothing new has to be plumbed through.**

**Against:** It puts a piece of model machinery on the screen. "Eight games" is a real football fact, not
a schema noun, so it stays on the right side of the line — but it is the most internal-sounding option
here, and once it is on the card you own explaining it.

---

### Option 6 — The reason, plus what it is not

> **Card:** The model waits for eight games before it values a player, and he's not there yet. That's
> about the season so far, not about him.
> **Preview:** Under eight games — not a rating
> **Row:** `—` with a chip reading **Under 8 games**

**For:** Directly says the thing you and I both want said out loud: an honest "not enough games" must not
read as a knock on the player. Two of these are on your roster and one starts against you. This is the
only option that refuses the misreading in the sentence itself.

**Against:** Three clauses. The rest of the product speaks in one. It is the wordiest thing on any card,
and the short forms lose the protective clause exactly where a fast scan happens.

---

### Option 7 — The reason with his own count

> **Card:** He's played 5 games. The model waits for eight before it puts a value on a player.
> **Preview:** 5 of 8 games
> **Row:** `—` with a chip reading **5/8 games**

**For:** The most useful of all of them to you as a manager. It tells you *how close* he is — a player at
7 is one week from a value; a player at 4 is half a season away. That is decision-relevant in a way none
of the others are, and it turns a dead state into a progress reading.

**Against — and this is a real cost, not a quibble:** **games played is not currently carried anywhere
the screen can reach it.** It is not in the player record and not in the payload; it lives only in the
model's own feature file. Plumbing it through is a producer change plus a contract change. **This option
does not ship tonight.** The others can.

---

## Still rejected, and now for a different reason

> ~~"Not enough data on him yet."~~

In v1 I rejected this as measurably false. **That argument was wrong and I withdrew it.** But the sentence
still shouldn't ship, for a smaller reason: **"data" is vague where "games" is exact.** It invites you to
wonder whether something is broken. If you want this shape, Option 5 is the same thought said precisely.

---

## Combinations worth knowing about

- **1 + 2** (v1's combination) — still available, still the best pairing **if you choose not to give the
  reason.**
- **5 + 2's clause** — the reason plus the explicit not-a-rating line. That is essentially Option 6, which
  is why 6 is written as its own option rather than a footnote.
- **3 + 5** — "Value unavailable" as the compact form in tight spaces, the eight-game sentence on the full
  card. Semantically consistent, different lengths per context. This is legal under the framing's
  "semantic equivalence, one unambiguous state per context" rule.

---

## My honest read — yours to overrule

**Option 5** is the one I would argue for. It is the most honest thing available, it cannot be read as a
verdict, it costs nothing extra to build, and it retires the blank-as-zero problem by explanation rather
than by protest. **Option 6** if you want the not-a-judgement line stated rather than implied.
**Option 7** is the best product and the only one that can't ship tonight — worth knowing it exists so you
can ask for it later rather than discovering it after 5 has shipped.

I would not pick **1** now that a reason is available, though it remains defensible and it is the
quietest thing on the screen.

**Tell me the number and the build starts.**
