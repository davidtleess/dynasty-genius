# Codex consolidated verification — Studio relay 009

Date: 2026-07-25
Scope: verification only; no implementation, source edit, commit, push, or wire use
Inputs:

- `/Users/davidleess/frontend-studio/proposals/009-RELAY.md`
- `/Users/davidleess/frontend-studio/proposals/009-RELAY-ADDENDUM.md`

## Addendum disposition

**Verdict: PARTIALLY CONFIRMED, but incomplete and not numerically reproducible as written. No P1–P6 verdict changes.**

The correction is directionally right: removing the 15 `ACTIVE_B` rows whose null xVAR was fabricated as `0.0` increases the positive age association in the xVAR rank-gap lane. The DVS result is exactly reproducible and is unaffected because those 15 rows never entered the DVS cohort.

The exact xVAR figures `+0.313 → +0.340` do **not** reproduce from the named frozen artifacts under the stated method. A read-only reconstruction using Studio's own frozen `board-data.js`, the pinned `league-20260724T132000Z` team matrix and snapshot, within-position average ranks, `gap = market rank − model rank`, and pooled Pearson correlation produced:

| Cohort | Studio addendum | Independent reproduction |
|---|---:|---:|
| xVAR, coerced zeros included | +0.313, n=269 | **+0.308, n=269** |
| xVAR, 15 `ACTIVE_B` nulls removed | +0.340, n=254 | **+0.327, n=254** |
| xVAR, all null-xVAR coercions removed | not reported | **+0.329, n=242** |
| DVS | +0.218, n=242 | **+0.217643, n=242** |

The frozen cohort counts are verified. Studio's board has 269 market-priced rostered skill players: 242 with DVS, 15 `ACTIVE_B` null-value rows, and **12 `PRE_MODEL` null-xVAR rows**. The current source cohort has one later addition, Rasheen Ali, which explains the otherwise observed 270-versus-269 count and is not an error in the addendum's frozen count.

Two defects remain in the correction:

1. **“Corrected” removes only one class of fabricated zeros.** The 12 `PRE_MODEL` null-xVAR rows remain ranked as genuine zero opinions after the stated 15-row removal. On the frozen board their removal changes `r` only from +0.327 to +0.329, so this does not reverse the qualitative result, but the stated corrected cohort is not clean of the P2 coercion mechanism.
2. **The opening explanation contradicts the verified DVS construction.** It says both correlations were computed over a population containing the 15 rows, while the next section correctly says the DVS lane excluded them by construction. The latter is verified.

The claim that the rerun strengthens the conclusion that DVS is “materially better matched to a dynasty price” is **OVERSTATED**. A lower bivariate age correlation supports only a narrower statement about age association in these two rank-gap constructions. It does not establish construct validity, and P4 independently confirms that DVS is a within-position score rather than an honest cross-position dynasty-price quantity.

The qualitative statement that age does not explain the whole gap remains reasonable as a descriptive bivariate observation: even Studio's larger reported correlation implies about 11.6% linear shared variance. “Contamination” remains interpretive rather than causal evidence.

Reproducer: `docs/validation/reproducers/verify_studio009_addendum.py`
Reproducer SHA-256: `9073ba4bbc1b316c4817fc6b1ac1a71be876195b2f0fba7083521eb6c0ba5bda`
External frozen inputs and their required hashes are declared in `docs/validation/evidence/README.md`; the reproducer refuses missing or mismatched inputs.
Addendum SHA-256: `7acd19b13d4a24622cf0355ba6413b914f38740caa2910a6634d26c5444283b2`

## Binding disposition

| ID | Verdict | Severity after verification | Disposition |
|---|---|---:|---|
| P1 | **OVERSTATED as written; two real residual defects confirmed** | **High** | Do not implement Studio's claimed universal read-path fix. Repair the closeout plan around mixed vintages, false freshness, and process-version drift. |
| P2 | **CONFIRMED** | **Critical** | Add an explicit fail-closed value-state ticket before any DG2 comparison work. |
| P3 | **CONFIRMED as a product-metric defect, not an implementation mismatch** | **High** | DG2 must separate lineup availability from dynasty-asset strength; S3-04/S3-05 do not currently finish that decision. |
| P4 | **OVERSTATED** | **High roadmap blocker; not a current false overall board** | Keep the ceiling repair; reject the premise that DVS itself is the cross-position quantity. |
| P5 | **REFUTED as an independent defect** | none | Correct P2/P3 inputs and recompute. Do not replace league-relative labels with within-roster normalization. |
| P6 | **CONFIRMED and under-severed** | **High / visual P1** | Add a separately owned whole-viewport framing ticket after P1/P2 data honesty is secured. |

The relay is valuable but not safe to accept verbatim. P2, P3, and P6 survive. P1 merges three different lifecycle failures under a read-path diagnosis that current source disproves. P4 merges a real ceiling defect with a false expectation of DVS. P5 proposes changing the meaning of a correctly league-relative signal.

## P1 — stale league surfaces

**Verdict: OVERSTATED as written.**

The live symptom reproduced exactly:

- the process listening on port 8000 served June-23 posture/matrix data and June-23 trade assets;
- its PID 7180 started **2026-07-14 19:22:38**, before commit `157fda868347ad041eba4ef6b00cafde340b4c2f` landed the marker-pinned reader on July 15;
- four posture changes reproduce against the July-25 accepted run: MDEF `BALANCED → CONTENDER`, Free Kelly `BALANCED → CONTENDER`, Seidmans Sasquatches `ASCENDING → REBUILDING`, Kissane's Team `CONTENDER → BALANCED`.

But “nothing reads” the runtime runs is false in current source:

- `app/api/routes/league_pulse.py:45-56,67-75` request-pins `load_production_league_set()` for posture and team matrix;
- `app/api/routes/trade.py:59-80,110-120` resolves the marker-pinned snapshot for the asset catalog;
- `src/dynasty_genius/league_capture.py:258-312` verifies marker shape and artifact digests before returning runtime paths.

A direct execution from the current checkout returned July-25 posture (`2026-07-25T13:20:06.183368+00:00`), matrix (`2026-07-25T13:20:06.157310+00:00`), and trade snapshot (`2026-07-25T13:20:04.296023+00:00`). The old live process had stale code loaded.

Three residual failures remain:

1. **Mixed-vintage League Pulse.** `league_pulse.py:59-60,75` still reads `league_opportunity_latest.json` outside the marker-pinned run. Current source therefore combines July-25 posture/matrix with a July-15 opportunity artifact whose inputs are June-23 posture/matrix. The page can contradict itself: the posture table is fresh while partner rankings/cards inherit old postures.
2. **False-fresh Roster Capacity.** `app/api/routes/roster_capacity.py:34-37,190-200` serves a static artifact and calls it `artifact_status="ok"` whenever its timestamps merely parse. It currently reports `ok` over a June-23 Sleeper snapshot; the file itself was last written July 14.
3. **Invisible process-version drift.** A corrected reader can remain absent from the live product indefinitely because health surfaces do not distinguish current source from a pre-change loaded process.

Therefore DG2-P-01's current “all four consumers read the newest capture” framing is not precise enough. The eventual closeout plan must separately prove:

- current loaded process code resolves the accepted marker;
- every League Pulse section has coherent source vintages, or visibly refuses/degrades;
- derivative artifacts such as Roster Capacity have refresh ownership and an age-based freshness rule, not just parseable timestamps.

## P2 — null ACTIVE_B value becomes zero

**Verdict: CONFIRMED, Critical.**

July-25 reproduction:

- 272 rostered skill rows;
- exactly **15** `ACTIVE_B` rows have both DVS and xVAR null;
- the coercion is broader than Studio measured: **27** rostered skill rows have null xVAR (15 `ACTIVE_B`, 12 legitimate `PRE_MODEL`) and all enter the same `_xvar()` path that fabricates `0.0`;
- all **15/15** false-grade rows become `raw_xvar: 0.0` in the team matrix;
- against the relay's July-24 FantasyCalc cache, they carry exactly **31,550** market-value units. A second independent run against a later cache saw 31,593; the invariant is the same 15 false zeros.

The two defects are directly located:

- `src/dynasty_genius/pvo_assembler.py:378-410` assigns `ACTIVE_B` before the low-games/dead-window branch; `:415-456` can null the value without resetting the grade/status.
- `src/dynasty_genius/team_value_matrix.py:18-20` converts any null xVAR to `0.0`; that value then drives lineup selection, team strength, positional summaries, posture, partner rankings, and roster-fit cards (`:52-105,153-220,243-289`).

Studio overstates one part of the blast radius. The dedicated divergence builder does **not** interpret these rows as model-low:

- `src/dynasty_genius/universe_market_divergence.py:37-50,111-117` requires non-null xVAR for model-backed cohorts;
- `:198-205` emits `UNAVAILABLE` when the value is absent.

So “every divergence readout” is false. The defect remains Critical because core league aggregates receive fabricated zeros and Player Detail says “modeled” without a value or degradation. The grade repair and null-propagation repair are related but not identical: changing the 15 false `ACTIVE_B` grades alone would leave the 12 correctly `PRE_MODEL` nulls fabricated as zeros.

Required planning ownership: a new Sprint-P honesty ticket (or a materially expanded P-01/S0-04 ticket) whose finish line preserves unavailable as unavailable through every aggregator, reconciles grade/status with value availability, names affected consumers, and proves no null is silently ranked as zero. This must precede DG2 rank/currency comparisons.

## P3 — IR/taxi excluded from dominant dynasty posture input

**Verdict: CONFIRMED as a product-metric defect, High.**

The implementation is internally consistent with its existing rule:

- `team_value_matrix.py:35-49,246-253` excludes IR/taxi from legal-lineup candidates and depth credit;
- `team_posture.py:28-37,116-135` makes `starter_weighted_xvar` 60% of posture;
- the code already computes all-asset alternatives (`team_value_matrix.py:254-272`) but does not use them for that dominant posture term.

The current asymmetric effect reproduces:

- roster 1 has **26.6%** of market value on IR/taxi versus a current league median **3.6%**, or **7.32×**;
- the legal lineup uses AJ Barner at TE (`-5.64`) while Tucker Kraft on IR is `+2.85`;
- it uses Tank Dell at superflex (`0.0`) while Fernando Mendoza on taxi is `+10.31`.

The Tank Dell half of Studio's flagship comparison is itself a P2 artifact: Dell is `PRE_MODEL` with null xVAR, not a genuinely valued zero. Mendoza's `+10.31`, Kraft's `+2.85`, Barner's `-5.64`, the 26.6% exclusion share, and the architectural coupling still reproduce, so removing that contaminated example does not defeat P3.

This is not a claim that an IR/taxi player should count as startable. The defect is using “can fill a legal lineup now” as the dominant answer to an offseason dynasty-asset-strength question, while the same number drives posture, position z-scores, and counterparty discovery. Separate questions need separate measures.

DG2-S3-04 currently asks for a league-legal optimal lineup, and S3-05 only requires eligibility states. Those tickets can both close while IR/taxi dynasty assets remain excluded from posture exactly as today. The plan needs an explicit decision/AC separating:

- current lineup availability; and
- dynasty roster/asset strength, including unavailable and taxi assets with their costs/status visible.

## P4 — DVS ceiling and cross-position use

**Verdict: OVERSTATED.**

The ceiling defect is confirmed and worse on July-25 data:

- 245 rostered skill players have DVS;
- **23**, not 12, are exactly `100.0`;
- they span market #2 Bijan Robinson through #158 Dallas Goedert;
- the top-50 DVS mix remains 19 TE / 14 WR / 9 RB / 8 QB.

The cause is explicit at `pvo_assembler.py:389-410`: projection divided by a position-specific P90 and clamped to 0–100. DG2-S3-03 legitimately owns removing bound-induced ties, though its stale “twelve players” measurement should be refreshed or written as a dated observation.

The second half is not a defect in DVS. DVS is deliberately normalized within position; the ratified cross-position layer is xVAR (`pvo_assembler.py:471-491`), and DG2's new assembled value is intended to replace the present inadequate cross-position quantity. Sorting DVS overall and finding a TE-heavy board demonstrates misuse of the field, not proof that DVS violated its contract.

No current surface presents an honest DVS overall rank. Therefore this is High as a blocker to a future apples-to-apples overall board, not a current High false-board defect. Do not “fix” DVS into the DG2 cross-position value by assumption.

## P5 — all four positions labelled deficit

**Verdict: REFUTED as an independent defect.**

The four values reproduce exactly, but the semantics are intentional:

- `team_value_matrix.py:143-150,208-220` defines each position against the 12-team league distribution;
- `docs/strategies/Phase17-Research-Draft.md:191-195` records that definition;
- `league_opportunity_map.py:154-175,249-299` matches David's league-relative deficit to another roster's league-relative surplus.

An all-around weak roster can truthfully be below the league threshold at all four positions. Fourteen WR roster slots do not prove a value surplus. Within-roster normalization would force every team to have a relative “surplus,” even when every group is weak, and would break the counterparty-fit meaning.

P2/P3 contaminate the input values and must be corrected before recomputation. At most, rename/copy can clarify “league-relative value deficit.” Do not create a new signal-definition ticket on Studio's proposed basis.

## P6 — League Pulse raw-render surface

**Verdict: CONFIRMED and under-severed: High / visual P1.**

Playwright at 1440×900 reproduced exactly:

- `document.body.scrollHeight = 43,634`;
- surface height 43,534.64 px;
- 11 partner rankings, 12 postures, 12 team-value blocks, and 31 opportunity cards;
- 48 visible `z_score` tokens and 18 `surplus_label` tokens;
- the mandatory mid-scroll viewport centers on raw `perspective_surplus_label`.

Screenshots:

- `docs/validation/evidence/2026-07-25-studio-009-league-pulse-top.png`
- `docs/validation/evidence/2026-07-25-studio-009-league-pulse-mid.png`
- `docs/validation/evidence/2026-07-25-studio-009-league-pulse-full.png`

Source confirms this is authored raw rendering, not an accidental serializer:

- `frontend/src/league-pulse/TeamValueOverview.tsx:9-21,36-75` renders allowlisted schema keys directly;
- `OpportunityCards.tsx:125-190` renders raw card types, evidence keys, score keys, and caveat tokens;
- the page is primary-nav reachable.

This was already recorded as a P0 defect in `docs/agent-ledger/2026-07-16.md:223-229`, including raw keys across all four League Pulse sections, but it has no current owner in the DG2 backlog. DG2-P-05 only fixes invisible picks inside one block; it does not repair the surface.

Because `PRODUCT.md` and `DESIGN.md` make raw schema vocabulary and a diagnostics-console viewport objective blockers, Medium is too low. A separate visual framing ticket is required, after P1/P2 establish truthful inputs. It must use whole-viewport and mid-scroll evidence; component-contract green cannot close it.

## Independent due-diligence reconciliation

A fresh, no-context reviewer independently returned:

- P2/P3/P6 **CONFIRMED**;
- P1/P4 **OVERSTATED**;
- P5 **REFUTED**.

That matches this consolidated verdict exactly. The reviewer additionally reproduced 48,669 px at 390×844 and found 2 px horizontal overflow; it upgraded P6 to High/P1. It ran focused backend 64/64 and frontend League Pulse 16/16, demonstrating that current tests encode contract conformance while missing mixed-vintage coherence and whole-viewport usability.

One judgment changed under attack: my first pass treated P3 as potentially overstated because the code follows its registered legal-lineup rule. The independent reviewer separated implementation conformity from product validity: the rule still answers the wrong question for offseason dynasty posture. The measured asymmetry and the fact that S3-04/S3-05 can close without separating the two questions make **CONFIRMED** the defensible verdict.

Independent report: `docs/validation/2026-07-25-studio-009-independent-review.md`
Independent report SHA-256: `499481a1151fc11931f2ea3bb4dc05c82cd7290bc132c6075e39cddcb4073ed0`

## Required closeout-plan delta — no implementation authorized

Before DG2 opens in a fresh session, the eventual closeout should place these items explicitly:

1. **P2 first:** fail-closed value availability and honest grade/status; blocks any rank/currency work.
2. **P1 split:** operational loaded-code proof, coherent League Pulse vintages, and age-based Roster Capacity freshness/refresh ownership.
3. **P3:** amend DG2 so lineup availability and dynasty asset strength are distinct quantities/uses.
4. **P4:** retain S3-03 ceiling retirement, refresh the dated count, and keep cross-position construction in the DG2 value decision.
5. **P6:** create a separately framed whole-viewport visual ticket; do not hide it inside backend cleanup or P-05.
6. **P5:** no ticket except optional copy clarification after P2/P3 recomputation.

This packet authorizes none of those edits. It is the due-diligence input Tower should use when running the closeout.
