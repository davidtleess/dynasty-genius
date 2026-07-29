# TW28-EVE — Framing v2: the players whose value the model withholds

**Author:** Claude Code · **Status:** framing v2, pre-RED. Frozen before routing.
**Authority:** David, 19:31 — *"do the framing and wording options tonight - perhaps we can build as
well."* Tower's transmittal: **"perhaps we can build" is appetite, not a commit word.**
**Chain:** v1 (`c82ec411…bca0e8`) → Codex NOT CLEAR, 8 findings (`3f84b671…c3b4c81`) → my disposition
(`modeled_blank_disposition_v1.md`, all eight accepted, three narrowed) → this v2.

**No code. No RED. Nothing committed. No wording chosen.**
Design foundation (`PRODUCT.md` + `DESIGN.md`) read via `impeccable` before any copy was drafted.

> **What changed from v1, up front.** The title changed, because the finding changed: the model does
> **not** come up empty on these players — it produces a forward projection and **withholds** the value
> derived from it, deliberately, below its own reliability floor. v1 said the opposite on three counts and
> each was my error: it claimed all projections were absent, claimed no cause existed anywhere, and
> claimed three surfaces shared one defect. All three are corrected below.

---

## 0. What this thread does NOT touch

**0.1 · Thread 2 / Unit C stays parked and commit-isolated — and the coupling is contract-level, not
cosmetic.** v1 called it "a single row" of Unit C's table. That was wrong. Unit C framing v4 assigns
**no degradation to all 581 modeled routes** (§3.4 branch 1) and its **falsifier 6** requires a modeled
row to carry no degradation. This thread deliberately contradicts branch 1 for 113 of those rows and
**invalidates v4's seed 6 outright**. Both threads touch `players.py`, `PlayerInspector.tsx`, the
player-detail contract, and their tests.

Thread 2 remains parked and shares no commit — unchanged, and David's standing instruction. **But v4
cannot resume unchanged after this lands: it requires a fresh amendment and a fresh challenge against
the resulting contract before its RED opens.** Recorded here for whoever picks it up. This is a durable
note, not a reopening.

**0.2 · The partial-coverage floor remains David's**, untouched. Nothing here sets or leans on a
coverage threshold.

**0.3 · The cross-producer valuation contradiction is a SEPARATE, David-owned item** (§4.3). It is more
severe than the defect this thread was opened for. It is named, measured, and **explicitly not folded
into this build.** Whether it opens is David's call and he has been told so in those terms.

**0.4 · Whether to repair or re-rule the eight-game conversion policy is NOT this thread's** (§3.3). That
is a model-contract question with its own governance. This thread changes what the screen says about the
policy's output, never the policy.

---

## 1. The situation — the manager's actual moment

David opens a player card mid-decision. For 113 players it tells him the player is **Modeled** and then
shows him nothing where the value goes.

Not fringe names: **Jayden Daniels, Malik Nabers, Garrett Wilson, Tyreek Hill, Kyler Murray, Calvin
Ridley, Jayden Reed, Braelon Allen, Trey Benson, Jaydon Blue.** Fifteen are rostered in his league; **two
are on his own roster** (Garrett Wilson, Braelon Allen); Jayden Daniels starts for another team.

**Thirty-one carry a live market price** — Jayden Daniels 7,375, Malik Nabers 6,398. On those cards the
market lane prints a large number and the model lane prints an empty space under a label saying the
player is modeled. The per-player model-vs-market margin is the product's core thesis; for these players
it does not exist and the surface does not say so.

The failure is not a missing value. Missing values are legitimate and this product exists to say so
honestly. The failure is that **the surface asserts a state that is not true.**

## 2. Measurement — mine, fresh, corrected

Source: the artifact the API resolves, `app/data/valuation_runtime/universe_pvo_runtime.json`,
`captured_at` `2026-07-28T13:30:04Z`, 12,203 rows.

| Fact | Value |
| :-- | --: |
| Modeled-route rows | 581 |
| — carrying a value | 468 |
| — **value withheld** (`dynasty_value_score` AND `xvar` both absent) | **113** |
| Rows with only one of the two absent | **0** |

Uniformly `ENGINE_B` / `ACTIVE_B` / identity-resolved with a Sleeper id. QB 25 · RB 28 · WR 42 · TE 18.

**Projections — corrected; v1 was wrong here.**

| Field | Present on |
| :-- | --: |
| `projection_1y` | 0 / 113 |
| **`projection_2y`** | **113 / 113** |
| `projection_3y` | 0 / 113 |

v1 said "all projections absent." I had probed only `projection_1y` and generalised. **Every one of the
113 carries a two-year projection** (Jayden Daniels: 13.071). The model is not silent on these players.
Any state rendering them as "no model output" replaces one false claim with another.

`top_drivers` non-empty on all 113; `counter_argument` present on 92.

**The count is not an invariant and no test may pin it.** The committed seed
(`app/data/valuation/universe_pvo_latest.json`, `captured_at` `2026-06-26`) measures **114 of 583** on the
identical predicate, with `projection_2y` present on 114/114. **The predicate is the contract; the count
is a reading.** David held me to this and it binds the RED (§6.9).

## 3. Why the value is withheld — and what the screen may say about it

### 3.1 The cause is known and governed — v1 said it was not

v1 claimed the system carried zero cause information. **False, and the error was mine.** The narrow point
holds — `valuation_status` is circular, defined from DVS absence at `universe_pvo_batch.py:52`. But the
cause lives elsewhere and is explicit.

Joining the 113 to the latest rows of `app/data/features_runtime/engine_b_features_runtime.csv` returns
113 rows, **every one below the governed conversion floor**:

| `games_t` | 4 | 5 | 6 | 7 | ≥ 8 |
| :-- | --: | --: | --: | --: | --: |
| players | 33 | 28 | 31 | 21 | **0** |

The floor is `ENGINE_B_MIN_GAMES_T = 8` (`engine_b_contract.py:107`). The assembler **deliberately
retains the Engine-B projection and withholds DVS** when a player is below the floor with no Engine-A
prior (`pvo_assembler.py:389-456`, gate at `:394-404`). Contract tests pin the behaviour
(`tests/contract/test_phase14_dvs.py:94-106`, `:119-128`). Every affected row carries the causal
dead-window caveat.

**This is not a bug. It is the model refusing to publish a number it does not trust on 4–7 games.** That
is the honesty discipline working exactly as designed — one layer below a surface that then misreports it.

### 3.2 What killed v1's argument, and what it opens

v1 argued "not enough data" was false because 53 of the 113 have complete inputs. **The argument was
wrong.** `signal_completeness` is the fraction of required fields **present**
(`player_value_object.py:100-105`); it says nothing about whether the present `games_t` clears a sample
floor. Presence and adequacy are different things and I conflated them.

**The consequence runs to David's decision, not just this document.** A cause-free sentence is now a
**choice available to him, not a constraint forced by the data.** He can be told honestly that these
players are below the model's own reliability floor. That widens his wording options and **he has been
told so.** Nothing here selects for him.

### 3.3 The policy question, named and not absorbed

Whether an eight-game floor is the right floor, and whether withholding DVS while publishing a
projection is the right pairing, are model-contract questions with their own governance. **Not this
thread's, not investigated here, not silently folded in.** Named for David as a separate item.

### 3.4 One verified non-defect

`universe_market_divergence.py:16` lists `MODEL_UNCERTAIN` in `MODEL_BACKED_STATUSES`, which reads
alarming. Both call sites (`:43-50`, `:111-117`) additionally require a present `xvar`, so all 113 are
excluded from the margin. **Checked before reporting; no alarm raised.** Independently confirmed by Codex.

## 4. The defect, precisely — corrected

### 4.1 Two surfaces share one derivation; a third is a different problem

The player-detail API decides "is this modeled?" from the route alone (`players.py:246-249`) and never
asks whether a value came out. Its degradation message (`:289-291`) is gated on `not modeled` and
**never fires** for these rows.

| # | Surface | Location | Today |
| :-- | :-- | :-- | :-- |
| 1 | Quick preview | `PlayerInspector.tsx:22-35` | **"Modeled"** — flat assertion |
| 2 | Full card, model lane | `ValuationTwoLane.tsx:47-56` | renders the value raw → **`<span></span>`**, a blank, not a dash. The `Model unavailable` fallback at `:59` fires only when the whole lane is absent, which it is not. |

**Both consume the same `PlayerDetailResponse`.** v1's "three surfaces, three independent derivations"
was wrong twice over: these two already share a derivation, and the third is not this population's
problem at all (§4.3).

**The contract is more open than v1 claimed.** `model_status` is `str` (`players.py:117`) and
`z.string()` (`zod.gen.ts:635`) — the producer emits two values; **the schema constrains none.** v1's
"two-value field requiring a contract change" overstated it.

### 4.2 The architectural choice — presented, NOT selected

Framing is problem-space work. v1 selected an architecture inside it, which is the drift the
framing-first rule exists to prevent. Both live options, with costs:

- **(A) Derive focal-value availability once in player detail**, consumed by its two surfaces. Bounded,
  touches one producer and two components, ships tonight if David picks a wording. Leaves the roster-audit
  contradiction untouched and unfixed.
- **(B) Unify the roster-audit data source first**, then seek one cross-surface state. Materially larger,
  crosses into the separate producer discrepancy (§4.3), and is not an evening-sized piece.

**Neither is selected here.** (A) is the scope of the word David gave; (B) depends on his §4.3 call.

### 4.3 The cross-producer contradiction — separate, David-owned, MORE SEVERE

The roster audit **does not read the runtime artifact.** It rebuilds through `assemble_pvo` with `age`
and `engine_b_score` and **no `games_t`** (`roster_auditor.py:644-649`, verified by me), so
`_below_games_gate` evaluates False and it **computes a DVS from the same projection** the player card
withholds.

Codex's exact reconstruction — **his numbers, not independently reproduced by me:**

| Player | Player card | Roster audit |
| :-- | :-- | :-- |
| Braelon Allen | blank / blank | 31.2 / −16.46 |
| Garrett Wilson | blank / blank | 77.6 / 17.0 |
| Jayden Daniels | blank / blank | 65.0 / 1.11 |

**The same player carries a real number on one screen and nothing on another, with nothing telling David
which to believe.** Two of the three are on his own roster.

The **players** overlap completely; it is the **defect** that differs. The roster audit is not an
unaffected surface — it is a differently affected one, and no wording change can touch it.

**This is worse than the defect this thread was opened for. Named, not absorbed. David's call.**

### 4.4 Composition rules

1. **Exactly one statement per row.** It replaces the focal values; it never stacks with another caveat.
2. **The two player-detail surfaces state the same truth** — **semantic equivalence and one unambiguous
   state per context**, not byte-identical prose. v1 required identical strings, which pre-decided part of
   David's wording choice and is not what the design foundation asks for. He may still choose one shared
   string; this framing does not choose it for him.
3. **The state distinguishes *focal values unavailable* from *no model output*.** The two-year projection
   is real, is preserved, and the model lane must not collapse to "Model unavailable."
4. A designed primitive state, never raw text (`DESIGN.md` §Components). A bare empty span is a defect
   under PRODUCT principle 6 regardless of what the card says.
5. Prose in Plex Sans; mono is numeric values only. No verdict hue, no green/red, no urgency motion.
   `decision_supported=false` untouched.

## 5. Mislead / nudge risks — unranked

v1 ranked "blank read as zero" severest. With §4.3 on the table that ranking is not supportable and it is
removed. **The two are not comparable on one axis: one is addressable by copy, the other is not
addressable by copy at all.** For the decision in front of David tonight — the wording — the first is
the operative one, and that is the only sense in which it leads.

1. **Blank read as zero.** An empty model cell beside a 7,375 market price can read as "Dynasty Genius
   rates him near nothing" — a verdict never issued, on David's own roster.
2. **Cross-producer contradiction** (§4.3). Not addressable by wording. Separate item.
3. **Erasing the projection.** A state that reads as "no model output" is a *new* false claim; the
   two-year projection is real.
4. **Asserting a cause the copy has not earned.** The cause exists (§3.1) but is a governed model policy;
   any surface sentence naming it must match what the floor actually is, not a paraphrase.
5. **Promising future coverage.** "yet", "coming soon", "pending" imply the model will get to him —
   a claim about future work and implicitly a judgement about who is worth modelling. *(Note: with §3.1
   known, a bounded statement about games played is no longer automatically a promise. The line is
   between a fact about this season and a commitment about the model's roadmap.)*
6. **Reading as a judgement about the player.** Real people David knows by name. Absence of a model
   output is a fact about the model, never about the athlete.
7. **Diagnostics leaking to the surface.** Naming the engine, route, marker, or pipeline breaks the
   scaffolding-hide law — this product's strongest anti-reference.
8. **Over-warning.** Two surfaces × one statement is right; × a stacked caveat block is the
   layered-caveats failure.

## 6. Falsification seeds — the RED matrix

**MEASURED-LIVE:**

1. A modeled-route player whose focal values are absent gets the honest state on **both** player-detail
   surfaces, semantically equivalent, one unambiguous state per context.
2. A modeled-route player **with** values (of the 468) gets **no** statement and renders unchanged — the
   over-correction control.
3. **Projection preservation** *(new, from finding 1)*: the affected player's `projection_2y` survives
   unchanged in the payload and remains rendered. The model lane must **not** collapse to "Model
   unavailable."
4. The model lane renders a **designed** state, never an empty span, when a focal value is absent.
5. One of the 31 with a market price renders the market number and the honest model state together, with
   no implied comparison.
6. Exactly one statement per row; nothing stacks beneath it.
7. Lexical control: no schema noun, no route or engine name, no diagnostics token; and no cause claim
   beyond whatever David's chosen wording earns.
8. `decision_supported=false` unchanged on every affected payload.
9. **The roster audit is out of this thread's assertions** *(from finding 3)*: no test in this RED
   asserts roster-audit behaviour for this population. Its contradiction is a separate item and must not
   be silently repaired or silently pinned here.

**PREDICATE, NOT COUNT** (David's binding constraint):

10. The suite asserts the **predicate**, never the literal 113. A run against the seed artifact — 114 of
    583, `projection_2y` on 114/114 — **must pass unchanged**. Required RED row.

**PROSPECTIVE** (no live population — synthetic by necessity):

11. **A one-null pair fails closed** *(inverted, from finding 8)*: `PlayerValueObject` declares DVS and
    `xvar` independently `Optional` with **no cross-field validator** (`player_value_object.py:76-91`),
    so the case is reachable by contract even though today's assembler derives `xvar` only from a present
    DVS (`:471-490`). It is a producer-invariant violation and must **fail closed at the producer/API
    boundary**, never resolve quietly to a display state. Malformed / cross-component-shape row of the
    robustness matrix (governance 02 §Falsification #8). v1 had this backwards.
12. A modeled-route player with values absent **and** no market price renders the model state and the
    existing market-unavailable state without the two merging into one claim.
13. A future consumer cannot re-derive availability from the route; the single derivation is the
    contract and the test names it.

## 7. No-Verdict check

The change **removes** an unearned assertion and adds no claim beyond what David's chosen wording earns.
No tier, grade, ranking, recommendation, or imperative. `decision_supported=false` untouched. Market data
enters no model path. H2 QB rushing is uninvolved and remains **UNDER TEST**.

The live risk is **negative** verdict-by-implication — "no value" read as "worth nothing" — controlled by
§5.1 and the wording choice.

## 8. Compounding-product lens

- **Daily-login value:** immediate. 15 of these players are rostered in his league and 2 are his; on any
  morning he opens one, he learns the truth instead of a false claim. No waiting period.
- **Refresh cadence:** unchanged. Rides the existing daily refresh — no new job, artifact, or cadence.
- **Compounding:** derived from data the artifact already captures daily; membership is already
  accumulating in the point-in-time record. Nothing overwritten, nothing new stored.
- **Guardrail:** compounds nothing into a decision signal. It removes a false claim.

## 9. Sequence

1. This v2 → **fresh Codex review** (v1's eight findings dispositioned in
   `modeled_blank_disposition_v1.md`, all accepted, three narrowed).
2. **David's wording pick** — now with the eight-game reason available to him as an honest option.
3. **David's call** on §4.3 (the cross-producer contradiction) and §4.2 (scope A or B).
4. Codex authors the RED over §6, preserving the MEASURED-LIVE / PREDICATE / PROSPECTIVE split, the §6.10
   no-literal-count guard, and the §6.11 inversion.
5. Claude implements GREEN; Codex reviews to an enumerated CLEAR.
6. Full-suite tollgate **including the FE gate**.
7. **Commit on David's separate fresh word. Push is a second separate word.** Neither is authorised now.
