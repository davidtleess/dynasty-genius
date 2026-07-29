# TW28-EVE — Framing v1: the players the model ran on and returned no value for

**Author:** Claude Code · **Status:** framing v1, pre-RED. **Authority:** David, 19:31 —
*"do the framing and wording options tonight - perhaps we can build as well."* Tower's transmittal
states plainly that "perhaps we can build" is **appetite, not a commit word**, and that commit and push
each require his separate fresh word.

**No code written. Nothing committed. No RED open. No wording chosen.**

Design foundation read for this version: `PRODUCT.md` + `DESIGN.md` via the `impeccable` skill, plus the
`product` register reference. This was done **before** any copy was drafted, per governance 02 §Required
Reading Order item 5.

---

## 0. What this thread does NOT touch

**0.1 · Thread 2 / Unit C stays parked and shares no commit.** Unchanged from TW28-EVE-1.
**The seam is named, not hidden:** framing v4 §3.4 branch 1 covers exactly this population (the modeled
routes, "may assert: nothing"). The two plans meet on that one line. This framing proposes nothing that
edits Unit C's table; it proposes a state Unit C's branch 1 does not currently distinguish. If David
later lands both, the interlock is a single row of that table — flagged now rather than discovered in
GREEN.

**0.2 · The partial-coverage floor remains David's**, untouched. Nothing here sets, implies, or leans on
a coverage threshold.

**0.3 · WHY the model returned no value is a separate question and I am not absorbing it.** See §3.3.
It is a model question. This thread is about what the screen says, not about repairing the model.

---

## 1. The situation — the manager's actual moment

David opens a player card on a weekday morning, mid-decision (trade, cut, waiver, draft). For 113
players the card tells him the player is **Modeled** and then shows him nothing where the value goes.

These are not fringe names. They include **Jayden Daniels, Malik Nabers, Garrett Wilson, Tyreek Hill,
Kyler Murray, Calvin Ridley, Jayden Reed, Braelon Allen, Trey Benson, Jaydon Blue**. Fifteen are
rostered in his league; **two are on his own roster** (Garrett Wilson, Braelon Allen); Jayden Daniels is
an active starter on another team.

**Thirty-one of them carry a live market price** — Jayden Daniels at 7,375, Malik Nabers at 6,398. On
those cards the market lane prints a large number and the model lane prints an empty space, under a
label that says the player is modeled. The per-player model-vs-market margin is the product's core
thesis; for these 113 it does not exist, and the surface does not say so.

The failure is not that a value is missing. Missing values are legitimate and this product is built to
say so honestly. The failure is that **the surface asserts a state that is not true** — and does it
three times, in three places, each computing the claim on its own.

## 2. Measurement — mine, fresh, this session

Source: the artifact the API actually resolves, `app/data/valuation_runtime/universe_pvo_runtime.json`,
`captured_at` `2026-07-28T13:30:04Z`, 12,203 rows.

| Fact | Value |
| :-- | --: |
| Modeled-route rows | 581 |
| — carrying a value | 468 |
| — **carrying no value** (`dynasty_value_score` AND `xvar` both absent) | **113** |
| Rows with only one of the two absent | **0** |

The 113 are uniformly `ENGINE_B` / `ACTIVE_B` / identity-resolved with a Sleeper id. Positions:
QB 25 · RB 28 · WR 42 · TE 18. All projections absent. `top_drivers` non-empty on all 113;
`counter_argument` present on 92.

**The count is not an invariant and no test may pin it.** The committed seed fallback
(`app/data/valuation/universe_pvo_latest.json`, `captured_at` `2026-06-26`) measures **114 of 583** on
the identical predicate. **The predicate is the contract; the count is a reading.** David held me to
this explicitly and it is a binding constraint on the RED.

**The artifact already records the honest fact.** These rows carry `no_internal_value_signal` (and
`no_market_overlay`) in their own caveats. Nothing needs to be computed fresh — the API drops a fact it
is already handed. That materially lowers the cost of this fix and it is the strongest evidence that the
defect is presentational, not analytical.

## 3. What may honestly be asserted — and what may not

### 3.1 What the system can substantiate

Only this: **a value does not exist for this player right now.** That is directly observable.

### 3.2 What it cannot

`valuation_status` is set at `universe_pvo_batch.py:52`:

```python
return "MODEL_SUPPORTED" if pvo and pvo.get("dynasty_value_score") is not None else "MODEL_UNCERTAIN"
```

The uncertain marker is **defined as the absence of a value**. It is circular and carries **zero cause
information**. Any sentence naming a reason would be invented at the surface — the exact defect Unit C
exists to stop, reappearing in a new place.

**This kills the most natural-sounding copy.** "Not enough data on him yet" is false as well as
uncited: **53 of the 113 have fully complete model inputs** and still produced no value. A shortage of
inputs is measurably not the explanation for the largest single group.

### 3.3 The cause question, named and NOT absorbed

Why a complete-input player produces no value is a real and possibly serious model question. It is not
this thread's, it has no measurement behind it tonight, and answering it is not required to stop the
surface lying. **Named for David as a separate item. Not investigated here, not fixed here, not
silently folded into scope.**

### 3.4 One verified non-defect

`universe_market_divergence.py:16` lists the uncertain marker in `MODEL_BACKED_STATUSES`, which looks
alarming. It is not: both call sites (`:46`, `:116`) additionally require a present `xvar`, so all 113
are excluded from the margin computation. **Checked before reporting; no alarm raised.** The margin
surface correctly produces nothing for these players.

## 4. The defect, precisely — one cause, three independent claims

The API decides "is this modeled?" from the route alone
(`app/api/routes/players.py:249`, `MODELED_ENGINE_PATHS`) and never asks whether a value came out. Its
degradation message (`:289-291`) is gated on `not modeled`, so for these 113 it **never fires**.

Three consuming surfaces then each derive their own claim, and none reads another's:

| # | Surface | Location | What it prints today |
| :-- | :-- | :-- | :-- |
| 1 | Quick preview panel | `PlayerInspector.tsx:23,29-30` | **"Modeled"** — a flat assertion |
| 2 | Full player card, model lane | `ValuationTwoLane.tsx:47,51-52` | `{model.dynasty_value_score}` raw → **nothing renders**. Not a dash. The `Model unavailable` fallback at `:59` fires only when the whole lane is absent, which it is not. |
| 3 | Roster audit row | `roster_audit_models.py:264` → `RosterAuditRow.tsx:37,39` | **"applies"** beside **"—"**, derived from `engine_used == "engine_b"` |

**This is the same shape as the Unit C inspector finding, and the size follows from it:** an API-only
fix reaches none of the three. Surface 2 is the worst of them — a genuinely blank cell beside a market
number is the reading most likely to be mistaken for a low value.

### 4.1 The architectural point

The defect is not three copy bugs. It is that **"does this player have a value" is derived three times
from a proxy** (the route, the engine name) instead of once from the fact. The durable fix computes it
in one place and has all three surfaces consume it. Anything less leaves a fourth surface free to
reinvent the same wrong claim tomorrow.

This implies a **contract change** — `model_status` is today a two-value field and cannot express
"modeled route, no value". A contract change requires the full cockpit cycle (governance 02 §When the
cockpit applies).

### 4.2 Composition rules (carried from Unit C's §3.5 — same law, same reader)

1. **Exactly one statement per row.** It replaces the value; it never stacks with another caveat.
2. **All three surfaces render the same statement** for a given player. Divergence between them is the
   defect, so agreement is the contract.
3. The statement is a **designed primitive state**, never raw text — `DESIGN.md` §Components. In the row
   grammar the focal-value slot still needs a designed occupant; a bare empty span is a defect under
   PRODUCT principle 6 regardless of what the card says.
4. Prose renders in Plex Sans, not mono — mono is numeric values only (`DESIGN.md` §Typography).
5. No verdict hue, no green/red, no urgency motion. `decision_supported=false` untouched.

## 5. Mislead / nudge risks

1. **Blank read as zero.** The severest risk. A manager who sees an empty model cell beside a 7,375
   market price can read it as "Dynasty Genius rates him near nothing" — a verdict the system never
   issued, on Garrett Wilson, on David's own roster. Any wording must make "no score" unmistakably
   distinct from "a low score."
2. **Inventing a cause.** §3.2. Every plausible-sounding reason is unsubstantiated; one is measurably
   false for 53 of the 113.
3. **Promising future coverage.** "yet", "coming soon", "pending" imply the model will get to him — a
   claim about future work, and implicitly a judgement about who is worth modelling.
4. **Reading as a judgement about the player.** These are real people David knows by name. Absence of a
   model output is a fact about the model, never about the athlete. David held me to this explicitly.
5. **Diagnostics leaking to the surface.** Naming the engine, the route, the marker, or the pipeline
   breaks the scaffolding-hide law (PRODUCT principle 6) — this product's single strongest anti-reference.
6. **Over-warning.** Three surfaces × one statement is right; three surfaces × a stacked caveat block is
   the layered-caveats failure (PRODUCT principle 7).

## 6. Falsification seeds — the RED matrix

**MEASURED-LIVE** (real rows in today's runtime):

1. A modeled-route player with no value gets the honest statement on **all three** surfaces, identically.
2. A modeled-route player **with** a value (of the 468) gets **no** statement and renders unchanged —
   the over-correction control.
3. The full card's model lane renders a **designed** state, never an empty span, when the value is absent.
4. The roster audit row does not print "applies" for a player with no value.
5. One of the 31 with a market price renders the market number and the honest model statement together,
   with no implied comparison between them.
6. Exactly one statement renders per player; nothing stacks beneath it.
7. Lexical control: the statement contains no cause word, no route or engine name, no schema noun, and
   no future-coverage promise.
8. `decision_supported=false` is unchanged on every affected payload.

**PREDICATE, NOT COUNT** (David's binding constraint):

9. The suite asserts the **predicate** ("a modeled-route player whose value is absent renders the honest
   state"), never the literal 113. A test run against the seed artifact — which measures 114 of 583 on
   the same predicate — **must pass unchanged**. This is the mechanical guard against pinning a moving
   number, and it is a required RED row.

**PROSPECTIVE** (no live population — synthetic by necessity):

10. A player with a value present and `xvar` absent, or the reverse — **zero rows today** — must resolve
    to a single declared state, not fall between the two branches.
11. A modeled-route player with no value and **no** market price renders the model statement and the
    existing market-unavailable state, without the two merging into one claim.
12. A fourth consumer added later cannot re-derive the claim from the route — the single source of truth
    is the contract, and the test names it.

## 7. No-Verdict check

The change **removes** an unearned assertion from 113 players and adds no new claim beyond
non-existence. No tier, no grade, no ranking, no recommendation, no imperative. Direction is not
implied. `decision_supported=false` is untouched. Market data enters no model path. The H2 QB-rushing
hypothesis is not involved and remains **UNDER TEST**.

The one live risk is **negative** verdict-by-implication — "no value" read as "worth nothing" — and §5.1
plus the wording choice are the controls. That is the specific thing to attack in the challenge round.

## 8. Compounding-product lens

- **Daily-login value:** immediate. On any morning David opens one of these 113 — likely, since 15 are
  rostered and 2 are his — he learns the truth instead of a false one. There is no waiting period.
- **Refresh cadence:** unchanged. This rides the existing daily refresh; it introduces no new job, no
  new artifact, no new cadence.
- **Compounding:** the honest state is derived from data the artifact already captures daily, so the
  membership of this group is already accumulating in the point-in-time record. Nothing is overwritten
  and nothing new needs storing.
- **Guardrail:** this compounds nothing into a decision signal. It removes a false claim. There is no
  overclaim surface here to guard.

## 9. Sequence

1. **This framing → Codex's adversarial challenge → my written disposition** (governance 02 §Strategy/UX
   framing first — the challenge and the disposition are both mandatory, since I authored the framing and
   will implement the GREEN).
2. **Wording options to David, in parallel, tonight.** He picks. I do not.
3. Codex authors the RED over §6, preserving the MEASURED-LIVE / PREDICATE / PROSPECTIVE split and the §6.9
   no-literal-count guard.
4. I implement GREEN; Codex reviews to an enumerated CLEAR.
5. Full-suite tollgate **including the FE gate** — three frontend files are in scope.
6. **Commit on David's separate fresh word. Push is a second separate word.** Neither is authorised now.
