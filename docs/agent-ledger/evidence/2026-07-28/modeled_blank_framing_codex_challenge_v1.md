# TW28-EVE — Codex challenge of modeled-blank framing v1

**Reviewer:** Codex (independent review lane)  
**Reviewed artifact:** `modeled_blank_framing_v1.md`  
**Reviewed SHA-256:** `c82ec411480aa7fd243d30b21a6e9dca62c589bd11013f425ee86dbe18bca0e8`  
**Disposition:** **NOT CLEAR**

No wording is proposed here. Exact David-facing copy remains David's decision. This
review clears or challenges framing content only; it schedules no RED, build, commit,
or push.

## Independently reproduced claims that hold

1. Runtime artifact
   `app/data/valuation_runtime/universe_pvo_runtime.json`
   (`captured_at=2026-07-28T13:30:04.081845+00:00`) has 12,203 rows,
   581 modeled-route rows, 113 with both `dynasty_value_score` and `xvar`
   null, and zero with only one of those two null. The 113 split QB 25 /
   RB 28 / TE 18 / WR 42; all are `ENGINE_B`, `ACTIVE_B`,
   identity-resolved, and Sleeper-keyed.
2. The seed
   `app/data/valuation/universe_pvo_latest.json`
   (`captured_at=2026-06-26T18:16:37.613749+00:00`) has 583 modeled-route
   rows, 114 with both focal values null, and zero with only one null.
   The count is a vintage reading, not a contract.
3. Exactly 53 runtime affected rows have
   `valuation.feature_completeness == 1.0`; all 113 carry
   `no_internal_value_signal`; all 113 have non-empty `top_drivers`;
   21 have no `counter_argument`.
4. The current market-divergence artifact gives 31 of the 113 a market
   price, including Jayden Daniels 7,375 and Malik Nabers 6,398. It gives
   every affected row an unavailable divergence. The code guards hold:
   `src/dynasty_genius/universe_market_divergence.py:43-50` and
   `:111-117` require non-null `xvar`, so these rows do not enter the
   margin or model cohort.
5. The player-detail API derives `modeled` from route only
   (`app/api/routes/players.py:246-249`) and therefore emits a model object,
   `model_status="modeled"`, and no degradation for these rows
   (`:265-284`). `PlayerInspector.tsx:22-35` prints the flat assertion.
   `ValuationTwoLane.tsx:47-56` renders the nullable DVS/xVAR values raw;
   a direct React static-render probe of a null child produced
   `<span></span>`, confirming a blank rather than a dash.

## Concrete findings

### 1. The framing erases a real model output: all 113 have a two-year projection

Framing §2 says “All projections absent” (`modeled_blank_framing_v1.md:64-66`).
The independent runtime probe found the opposite:

- `projection_1y`: non-null on 0/113
- `projection_2y`: non-null on **113/113**
- `projection_3y`: non-null on 0/113

The seed has the same shape: `projection_2y` is non-null on 114/114. Jayden
Daniels, for example, has `projection_2y=13.071` while DVS/xVAR are null.
The producer preserves that projection at
`src/dynasty_genius/universe_pvo_batch.py:176-187`; the assembler receives it
from Engine B at `src/dynasty_genius/pvo_assembler.py:378-383`.

This breaks the title/manager story whenever “no value” is allowed to mean “no
model output,” and it makes §4.2's “statement replaces the value” underspecified.
The state must distinguish **DVS/xVAR unavailable** from **model projection
unavailable**, preserve the real projection, and add a measured-live
projection-preservation falsifier. It must not turn a partially populated model
lane into “model unavailable.”

### 2. The feature-completeness argument does not disprove sample insufficiency

The narrow claim that `valuation_status` itself carries no cause holds:
`src/dynasty_genius/universe_pvo_batch.py:50-52` defines
`MODEL_UNCERTAIN` from DVS absence.

The broader claims do not hold:

- Framing §3.2 says 53 fully complete rows make “not enough data” false
  (`modeled_blank_framing_v1.md:92-98`).
- Framing §2 calls the defect presentational, not analytical (`:73-76`).
- Framing §3.3 says the cause question has no measurement tonight (`:100-105`).

`signal_completeness` is only the fraction of required fields **present**
(`src/dynasty_genius/models/player_value_object.py:100-105`;
`src/dynasty_genius/pvo_assembler.py:258-266`). It says nothing about whether
the present `games_t` meets a sample-size floor.

Joining the 113 affected DG ids to the latest per-player rows in
`app/data/features_runtime/engine_b_features_runtime.csv` produced exactly
113 rows, all with `games_t` below the governed conversion floor:

- games 4: 33
- games 5: 28
- games 6: 31
- games 7: 21
- games 8 or more: 0

The floor is `ENGINE_B_MIN_GAMES_T = 8`
(`src/dynasty_genius/models/engine_b_contract.py:105-107`). The assembler
deliberately retains the Engine-B projection but withholds DVS when the player
is below that floor and has no Engine-A prior
(`src/dynasty_genius/pvo_assembler.py:389-456`). Contract tests pin that
behavior at `tests/contract/test_phase14_dvs.py:94-106` and `:119-128`.
Every affected row also carries the causal dead-window caveat.

The refusal to repair or re-rule this conversion policy inside a surface task is
correct. The rationale is not. Framing v2 must stop saying the source contains
zero cause information, stop using completeness to rule out sample insufficiency,
and stop declaring the defect exclusively presentational. It may keep the
surface copy cause-free without claiming the repo lacks a cause.

### 3. The roster audit is not a third rendering of this population

Framing §4 says all three surfaces derive the same wrong claim and specifically
that the roster row prints “applies” beside a dash
(`modeled_blank_framing_v1.md:120-130`).

The roster audit does **not** consume the runtime PVO. It independently calls
`score_inference_partition`, then invokes `assemble_pvo` with only `age` and
`engine_b_score` (`app/services/roster_auditor.py:608-649`). Because that path
omits `games_t`, `_below_games_gate` is false
(`src/dynasty_genius/pvo_assembler.py:394-404`) and it computes DVS from the
same projection.

Exact reconstruction of the roster-audit assembly path for the two affected
players on David's roster produced:

| Player | Runtime detail DVS/xVAR | Roster-audit assembly DVS/xVAR |
| :-- | :-- | :-- |
| Braelon Allen | null / null | 31.2 / -16.46 |
| Garrett Wilson | null / null | 77.6 / 17.0 |

A second probe for Jayden Daniels produced DVS 65.0 / xVAR 1.11 instead of the
runtime null/null pair. `model_status_applies` is true on those reconstructed
roster rows because `engine_used=="engine_b"`
(`app/api/routes/roster_audit_models.py:261-265`), but it sits beside a number,
not a dash.

Therefore the claimed three-surface population is false. More seriously, the
repo can show **different numeric valuation availability for the same player**
on player detail and roster audit. That cross-producer contradiction is a more
severe risk than the local “blank read as zero” ambiguity in §5.1.

Framing v2 must remove roster audit from the asserted same-population surface
fix unless a live response probe proves an actually affected roster row. It
must name the cross-producer valuation inconsistency as a separate
David-owned/model-contract item, not silently force the player-detail state
onto the roster audit.

### 4. The “blank read as zero” severity ordering is no longer supportable

The blank-cell risk is real. It is not established as the severest risk after
finding 3. A local ambiguity can be corrected in the detail contract; an
actual same-player contradiction between null DVS and numeric DVS can make
David trust whichever surface he happened to open.

Section 5 should present both risks without ranking one as severest until the
producer discrepancy is dispositioned. Wording options aimed only at
distinguishing blank from zero do not cover the cross-surface contradiction.

### 5. Section 4.1 locks a solution and misstates the current contract

Framing is problem-space work, but §4.1 selects “one derived source of truth
consumed by three surfaces” and says this necessarily changes a two-value
`model_status` contract (`modeled_blank_framing_v1.md:132-141`).

Two corrections:

1. Inspector and full detail already consume the same `PlayerDetailResponse`;
   the API is their common derivation. Roster audit is a different endpoint
   with a different producer.
2. `PlayerDetailResponse.model_status` is not a closed two-value type. It is
   `str` in Pydantic (`app/api/routes/players.py:114-122`) and `z.string()` in
   the generated frontend contract
   (`frontend/src/lib/api/zod.gen.ts:623-638`). The producer currently emits
   two values; the schema does not constrain them.

Any semantic change still requires cockpit review, but a new enum is not the
only defensible architecture. The framing must present the real choice:
derive an explicit focal-value availability state once in player detail for
its two consumers, or first unify the roster-audit data source and then seek
one cross-surface state. The latter is materially larger and crosses into the
separate producer discrepancy. Do not select it inside framing.

### 6. The parked Unit-C coupling is contract-level, not one table row

The new framing says the interlock is “a single row” of Unit C's table
(`modeled_blank_framing_v1.md:18-23`). Unit-C framing v4 does more than that:

- branch 1 assigns no degradation to all 581 modeled routes
  (`identity_honesty_fix_framing_v4.md:91-100`);
- falsifier 6 requires a modeled row to carry no degradation
  (`identity_honesty_fix_framing_v4.md:185-190`);
- both threads touch `players.py`, `PlayerInspector.tsx`, the player-detail
  contract, and their tests.

This thread deliberately contradicts branch 1 for 113 rows and invalidates
Unit C's existing seed 6. Thread 2 may remain parked, separate, and
commit-isolated, but v4 cannot resume unchanged after this thread lands. The
framing must record that Unit C requires a fresh amendment/challenge against
the resulting contract before its RED opens.

### 7. Byte-identical copy across contexts is not an earned constraint

Sections 4.2 and 6 require the same statement “identically” on all three
surfaces (`modeled_blank_framing_v1.md:143-152`, `:173-181`). The design
foundation requires consistent truth, designed states, lane isolation, and no
stacked caveat wallpaper. It does not require byte-identical prose in a quick
preview, a full model lane, and a compact table.

That constraint also pre-decides part of David's wording choice while the
framing says wording is his. Replace literal identity with **semantic
equivalence and one unambiguous state per context**. David may still choose
one shared string, but the framing must not choose that for him.

### 8. Prospective seed 10 is a contract hole, not a normal third state

The partial-pair case is not unreachable by contract:
`PlayerValueObject` declares DVS and xVAR independently nullable with no
cross-field validator
(`src/dynasty_genius/models/player_value_object.py:76-91`), and
`build_universe_pvo_batch` accepts plain PVO dictionaries
(`src/dynasty_genius/universe_pvo_batch.py:127-145`).

The current assembler does establish an intended dependency: xVAR is derived
only when DVS is non-null
(`src/dynasty_genius/pvo_assembler.py:471-490`). A one-null pair therefore
belongs in the malformed/cross-component-shape row of the robustness matrix.
It should fail closed at the producer/API boundary (or be explicitly
normalized by a ratified contract), not quietly “resolve to a single declared
surface state.” Keep the synthetic seed, but change its expected result to
enforce the invariant.

## Required v2 disposition

Please answer each finding accept/reject with cited reasons, issue a frozen v2,
and request a fresh review. No RED opens from this review.

