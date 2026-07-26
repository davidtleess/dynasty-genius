# Independent adversarial review — Studio 009 relay

Date: 2026-07-25
Repository: `/Users/davidleess/dynasty-genius-product`
Proposal: `/Users/davidleess/frontend-studio/proposals/009-RELAY.md`

## Headline

Disposition: **P2, P3, and P6 CONFIRMED; P1 and P4 OVERSTATED; P5 REFUTED as an independent defect.**

The relay found three real failures, but it conflates several causes:

1. P1's claimed read-path defect was fixed on July 15. The current checkout reads the marker-pinned daily run. The existing app process initially reached during this review still served the old June paths, which means that process had not loaded the current code. The remaining current-code defect is different and more subtle: League Pulse mixes July-25 posture/matrix rows with a July-15 opportunity artifact built from June-23 inputs, while Roster Capacity calls a June-23 snapshot `artifact_status="ok"`.
2. P2 is a two-stage false-state bug: the assembler leaves an injured/short-season veteran graded `ACTIVE_B` after its value is nulled, and `team_value_matrix._xvar` then turns that null into `0.0`. The divergence layer does fail safely to unavailable, so the relay's “every divergence readout” scope is too broad.
3. P3 is not just “IR/taxi excluded.” The architectural mistake is using a current legal-lineup view as 60% of an offseason dynasty-posture classifier despite already computing alternative all-asset views.
4. P4 accurately identifies clipping, but incorrectly calls DVS's position-specific scope a defect. The ratified Phase-14/15 design assigns cross-position comparison to xVAR, not DVS.
5. P5 asks a league-relative label to become a within-roster label. The present values correctly say roster 1 is below league strength at all four positions. Upstream P2/P3 contaminate those values, but the label logic is not independently wrong.
6. P6 is more severe than reported. It is a directly reachable, 43,634 px desktop / 48,669 px mobile diagnostics dump and violates explicit design blockers.

## Method and evidence

- Read governance/design sources first: `02` v1.3.0, `00` v1.1.0, `01` v1.0.0, `03` v1.1.0, `PRODUCT.md`, `DESIGN.md`, `AGENT_SYNC.md`, and the 2026-07-25 ledger.
- Read all P1-P6 implementation paths and current runtime/seed artifacts.
- The pre-existing server at `127.0.0.1:8000` initially returned June-23 League Pulse sources exactly as relayed, then exited. I did not mutate or restart it.
- Launched a separate diagnostic instance from the current checkout on port 8002. It served July-25 posture/matrix data and was stopped after each probe.
- Rendered League Pulse in headless Chromium:
  - desktop 1440×900: `document.body.scrollHeight = 43,634`
  - mobile 390×844: `document.body.scrollHeight = 48,669`, document width 392 px
  - screenshots: `docs/validation/evidence/2026-07-25-studio-009-independent-desktop.png`, `docs/validation/evidence/2026-07-25-studio-009-independent-mid-scroll.png`, `docs/validation/evidence/2026-07-25-studio-009-independent-mobile.png`
- Focused validation:
  - backend: **64 passed**, 1 unrelated sklearn pickle-version warning
  - frontend League Pulse unit tests: **16 passed**

Those passing tests demonstrate contract conformance; they do not rebut the runtime data or visual defects.

---

## P1 — League surfaces serve June-23 artifacts while fresh runs exist

**Verdict: OVERSTATED**

### What reproduced

The original running process returned:

- League Pulse posture/matrix: `2026-06-23T13:17:30...`
- the same four posture differences in the proposal were reproduced against the July-25 run:
  - MDEF `BALANCED → CONTENDER`
  - Free Kelly `BALANCED → CONTENDER`
  - Seidmans Sasquatches `ASCENDING → REBUILDING`
  - Kissane's Team `CONTENDER → BALANCED`

The accepted daily marker is now `league-20260725T132000Z`, source capture `2026-07-25T13:20:00.275676+00:00`, status `ok`.

The isolated server started from the current checkout returned:

| Source | Timestamp |
|---|---|
| League Pulse team posture | 2026-07-25T13:20:06.183368+00:00 |
| League Pulse team value matrix | 2026-07-25T13:20:06.157310+00:00 |
| Trade asset snapshot | 2026-07-25T13:20:04.296023+00:00 |
| League Pulse opportunity artifact | 2026-07-15T00:40:23.591631+00:00 |
| Roster Capacity sleeper snapshot | 2026-06-23T13:17:20.007866+00:00 |

### Cause and framing

The relay's root-cause sentence, “Nothing reads them,” is false in the current repository:

- `app/api/routes/league_pulse.py:45-56,67-74` resolves and request-pins `load_production_league_set()`.
- `app/api/routes/trade.py:59-80,118-120` reads the same marker-pinned snapshot.
- `src/dynasty_genius/league_capture.py:258-290,295-312` validates `ready_latest.json`, every digest, and the exact artifact set before returning the runtime paths.
- `src/dynasty_genius/league_capture.py:224-242` is the producer-side ready-marker publication.

That read-path landed in commit `157fda8` on July 15. The initially reached server was therefore a stale long-running process with pre-fix modules loaded, not evidence that the current code ignores the runtime store.

Two real current-code defects remain:

1. **Mixed-vintage League Pulse.** `app/api/routes/league_pulse.py:59-60,75` still reads `league_opportunity_latest.json` directly. That artifact reports `captured_at=2026-07-15`, but its own sources are June-23 team matrix/posture. The same API response therefore shows July-25 posture/matrix sections and June-23-derived partner rankings/cards.
2. **Roster Capacity false freshness.** `app/api/routes/roster_capacity.py:35-37,190-200` serves one static scorecard and calls it `ok` if its timestamps merely parse. It never checks age. The current response says `artifact_status="ok"` over a June-23 Sleeper snapshot. The producer explicitly has no scheduler (`scripts/run_roster_capacity_audit.py:15,53-55`).

### Reachability and user impact

- League Pulse is directly reachable from the main rail and `?surface=league-pulse`.
- Trade asset lookup is current under current code.
- Roster Capacity is directly reachable and silently labels month-old input “ok.”
- Partner rankings and opportunity cards in current League Pulse still inherit the four old posture labels even while the posture table below them shows the new labels. This is an internal contradiction on one page, not merely a stale badge.

### Severity

**Critical is not justified for the claimed universal/root-cause framing. High is justified for the remaining mixed-vintage League Pulse plus false-fresh Roster Capacity.** The stale-process condition also needs an operational code-version/process-restart signal; otherwise corrected reader code can remain invisible indefinitely.

---

## P2 — `ACTIVE_B` players return null value and league matrix stores `0.0`

**Verdict: CONFIRMED**

### Reproduced measurements on July-25 runtime

- rostered skill players: **272**
- `ACTIVE_B` with both DVS and xVAR null: **15**
- all 15 stored in the July-25 team matrix as `raw_xvar: 0.0`: **15/15**
- current FantasyCalc value carried by those 15: **31,593**

Top rows remain material:

| Player | Market rank | Market value | Matrix raw_xvar |
|---|---:|---:|---:|
| Jayden Daniels | 9 | 7,396 | 0.0 |
| Malik Nabers | 17 | 6,611 | 0.0 |
| Garrett Wilson | 44 | 3,984 | 0.0 |
| Kyler Murray | 80 | 2,811 | 0.0 |
| Malik Willis | 90 | 2,411 | 0.0 |

`GET /api/players/8146` on current code returns:

- `model_status="modeled"`
- `model_grade="ACTIVE_B"`
- `projection_2y=11.255`
- `dynasty_value_score=null`
- `xvar=null`
- `degradation=null`

The market lane is available, but divergence correctly returns `status="unavailable", delta=null`.

### Cause

There are two coupled defects:

1. `src/dynasty_genius/pvo_assembler.py:378-410` assigns `ACTIVE_B` before Dead Window handling. When `games_t < 8`, `:415-456` may null DVS because no Engine-A prior exists, but it never resets the grade/status. This contradicts the declared contract at `src/dynasty_genius/models/engine_b_contract.py:104-107`: retain Engine-A DVS or stay `PRE_MODEL`.
2. `src/dynasty_genius/team_value_matrix.py:18-20` converts any missing xVAR to `0.0`; `:181-200` publishes that fabricated zero as `raw_xvar`.

The player surface then calls every engine-path row modeled solely from route membership at `app/api/routes/players.py:246-249,265-284`; it does not degrade when both primary values are null.

### Reachability and user impact

- Directly visible in Player Detail as “modeled” with no value and no degradation.
- False zeros feed best-lineup selection, team strength, position z-scores, posture, partner rankings, and roster-fit cards through `team_value_matrix.py:52-93,153-220,244-289`.
- The divergence engine does **not** fabricate a model-low signal for these rows; it safely reports unavailable. The relay's “every divergence readout” claim is therefore overstated, but the team-matrix contamination remains severe.
- `ACTIVE_B` is not literally the highest possible grade (`ACTIVE_B_VALIDATED` exists), but it still falsely states an active model-backed valuation.

### Severity

**Critical is justified.** This violates the constitutional distinction between unavailable and low and corrupts core league aggregates with plausible-looking zeros.

---

## P3 — starter xVAR excludes IR/taxi and disproportionately hits roster 1

**Verdict: CONFIRMED**

### Reproduced measurements on July-25 runtime

- roster 1 market value in IR/taxi: **26.6%**
- league median: **3.67%**
- ratio: **7.24×**
- excluded top-100 assets:
  - Garrett Wilson, market #44, IR
  - Fernando Mendoza, market #45, taxi
  - Tucker Kraft, market #61, IR

Current best-legal lineup still starts:

- AJ Barner at TE, xVAR **−5.64**, while Tucker Kraft (IR) is **+2.85**
- Tank Dell at SUPER_FLEX, xVAR **0.0**, while Fernando Mendoza (taxi) is **+10.31**

Roster 1 views:

- `starter_weighted_xvar = 97.39`
- `top_n_xvar = 116.19`
- `total_xvar_capped = 117.98`

### Cause

- `src/dynasty_genius/team_value_matrix.py:35-49` explicitly excludes IR/taxi from legal-lineup candidates.
- `:246-253` also excludes them from depth credit.
- `src/dynasty_genius/team_posture.py:28-37,116-135` makes `starter_weighted_xvar` **60%** of posture.
- Taxi gets only a separate 5% stash term at `team_posture.py:66-72`; IR gets no analogous dynasty-strength representation.

The key framing correction is that the system already computes all-asset alternatives (`team_value_matrix.py:254-272`). The defect is not inability to value IR/taxi in aggregate; it is choosing the current-lineup view as the dominant offseason dynasty-comparison input.

### Reachability and user impact

Posture labels, partner scores, position z-scores, and roster-fit cards all inherit the distorted starter view. The skew lands most heavily on the product's only user's roster. In July, IR/taxi roster designation is not equivalent to dynasty value being absent.

### Severity

**High is justified.** It is a live decision-surface distortion with a measured, highly asymmetric effect. It should remain distinct from an in-season “can I field this lineup?” view.

---

## P4 — DVS saturates at 100 and is not cross-position comparable

**Verdict: OVERSTATED**

### Reproduced measurements on July-25 runtime

The fresh runtime is worse than the proposal's stale-process count:

- rostered skill players with non-null DVS: **245 of 272**
- exactly DVS 100.0: **23**, not 12
- capped players span market #2 Bijan Robinson through market #158 Dallas Goedert
- position medians / p75:
  - QB 74.1 / 81.45
  - RB 56.25 / 75.30
  - WR 66.53 / 75.80
  - TE 81.4 / 100.0
- top 50 by DVS: **19 TE / 14 WR / 9 RB / 8 QB**
- market top 50: **4 TE / 16 WR / 14 RB / 16 QB**

The clipping mechanism is explicit at `src/dynasty_genius/pvo_assembler.py:389-410`: predicted two-year PPG divided by a position P90, clamped to 0–100. P90 constants are position-specific at `src/dynasty_genius/models/engine_b_contract.py:19-29`.

### Why the framing is overstated

Saturation is a real information-loss defect for rank discrimination. Cross-position non-comparability, however, is not an accidental defect in DVS:

- Phase-14's ratified spec explicitly defines per-position P90 DVS and says cross-position work is Phase 15 (`docs/superpowers/specs/2026-05-16-phase14-dvs-normalization.md:34-44,264`).
- `dvs_pct` is explicitly within-position (`scripts/compute_dvs_pct_batch.py:1-5,20-35`).
- Phase 15 introduced xVAR for cross-position comparison using position replacement baselines and scarcity multipliers (`src/dynasty_genius/models/engine_b_contract.py:31-52,71-89`; `pvo_assembler.py:474-490`).

Therefore a 38%-TE overall DVS board demonstrates misuse of DVS for a job it was not contracted to do. It does not by itself prove the DVS per-position calibration is wrong.

### Reachability and user impact

Raw DVS is reachable in Player Detail, and the ceiling creates visible ties. No current user surface honestly presents DVS as a cross-position overall rank. The issue blocks the requested model-vs-market overall board, but it is a roadmap/value-layer limitation rather than a current false overall ranking.

### Severity

**High is justified as a blocker for any overall-rank initiative; it is overstated as an existing High live-surface defect.** The true corrective surface is the DG2 dynasty-horizon/cross-position value layer (or a validated successor), not pretending position-normalized DVS is universal.

---

## P5 — roster 1 is labelled deficit at all four positions

**Verdict: REFUTED as an independent defect**

### Reproduced values

The four July-25 values exactly reproduce:

- QB z −0.821, deficit
- RB z −0.799, deficit
- WR z −1.187, deficit
- TE z −1.268, deficit

But their league ranks support the labels:

| Position | Roster-1 model-value rank |
|---|---:|
| QB | 10 of 12 |
| RB | 9 of 12 |
| WR | 11 of 12 |
| TE | 10 of 12 |

### Why the defect claim fails

`src/dynasty_genius/team_value_matrix.py:208-220` intentionally standardizes each position against the league, and `:143-150` labels z < −0.75 deficit. `src/dynasty_genius/league_opportunity_map.py:16-18,48-62,260-295` uses the same league-relative thresholds to match David's below-league position with a counterparty's above-league position.

An all-around weak roster can truthfully be below league strength at every position. Counting 14 WRs does not establish a model-value surplus. Normalizing within the roster would force every roster to have a relative “surplus” even when all four groups are below league strength, breaking the counterparty comparison semantics.

The inputs are contaminated by P2's null-to-zero behavior and P3's IR/taxi exclusion. Those must be fixed and the z-scores recomputed. That does not make the threshold/label algorithm a separate defect.

### Reachability and user impact

The label is reachable in Team Value Overview and opportunity-card evidence. It is coarse and the name could be clearer (“league-relative value deficit”), but the raw z-score is preserved and distinguishes the four positions.

### Severity

**Medium is not justified.** At most this is a P3 copy/semantic-clarity issue after upstream P2/P3 are corrected.

---

## P6 — League Pulse is a 43,634 px key/value dump

**Verdict: CONFIRMED**

### Reproduced measurements

At 1440×900 from the current checkout:

- body/document scroll height: **43,634 px**
- partner cards: **11**
- posture cards: **12**
- team-value cards: **12**
- opportunity cards: **31**

At 390×844:

- scroll height: **48,669 px**
- document width: **392 px** (2 px horizontal overflow)
- the full navigation remains expanded, including a visible `DEVELOPER / Project Tracker` row

The desktop and mandatory mid-scroll screenshots show the exact payload grammar reported: `partner_score`, `complementarity_score`, `perspective_position_z`, `ROSTER_SURPLUS_DEFICIT_MATCH`, `future_pick_values_deferred`, etc.

### Cause

This is not accidental JSON serialization; it is hand-authored payload rendering:

- `frontend/src/league-pulse/PartnerRankings.tsx:10-23,40-79` emits raw score/evidence keys in repeated `<dl>` rows.
- `frontend/src/league-pulse/TeamValueOverview.tsx:9-21,36-75` emits raw value/age/pick/z-score keys.
- `frontend/src/league-pulse/OpportunityCards.tsx:20-65,141-190` emits raw card types, rationales, evidence keys, score keys, and caveat tokens.
- `frontend/src/league-pulse/LeaguePulse.tsx:64-107` renders every collection sequentially with no progressive disclosure.
- `frontend/src/league-pulse/LeaguePulse.css:1-58` styles only the shell/header/mitigation. It defines no layout for partner, posture, value, or opportunity cards.

The source's “strict allowlist” comments limit leakage volume; they do not turn schema names into manager-facing information design.

### Contract contradiction and reachability

League Pulse is directly in the primary nav (`frontend/src/shell/AppShell.tsx:177`; URL slug in `useUrlSurfaceState.ts:12`).

It contradicts:

- `PRODUCT.md:28,36,43-49`: never a developer diagnostics console; no raw schema nouns/snake_case; fantasy-native rows and manager prose.
- `PRODUCT.md:51-52`: mobile first-class; whole viewport is the review unit.
- `DESIGN.md:37-47`: 32 px rows, depth behind interaction, mobile bottom-sheet/collapsed-nav, reusable primitives.
- `DESIGN.md:64-66`: visible raw schema tokens and diagnostics on a user route are objective blockers; zero P0/P1 findings is required.

The header's “EXPERIMENTAL” and “Diagnostic Workspace” disclosure does not license the design violation; scaffolding-hide proportionality explicitly applies even to honest diagnostics.

### Severity

**Medium is too low. High/P1 is justified.** This is the only current UI answer to the counterparty question, is directly reachable, and fails the project's objective visual blockers. It is contract-green but not a usable or visually shippable surface.

---

## Missed coupling / contradictions

1. **Process-version drift is invisible.** The old app process served June seeds while current source and the marker were correct. Health/API responses expose artifact vintages but not the loaded commit/code version, so a process restart failure is indistinguishable from a reader bug.
2. **League Pulse is internally mixed-vintage.** Current posture/matrix sections are July 25; partner rankings/cards are built from June-23 posture/matrix. Fixing the top-level reader does not make the surface coherent.
3. **Roster Capacity's freshness check is lexical, not temporal.** A parseable month-old timestamp becomes `artifact_status="ok"`.
4. **P2's false zero does not contaminate every path equally.** Player Detail preserves null; divergence fails unavailable; Team Value Matrix fabricates zero. The fix must preserve null through every aggregator, not merely change the grade.
5. **P3 already has an unused comparison view.** `top_n_xvar` and `total_xvar_capped` include IR/taxi. The product currently computes both dynasty-asset and lineup views, then uses only the lineup view for the dominant posture input.
6. **P5 is downstream of P2/P3.** Reworking label semantics before correcting the underlying values would encode today's corruption into a new rule.
7. **P4's DVS board would violate its own contract.** The relay correctly refuses to ship it, but the proposed diagnosis should point to the missing cross-position dynasty-horizon value layer rather than mutate DVS into a role already assigned to xVAR.
8. **Tests encode the dump.** Backend 64/64 and frontend 16/16 pass while P1 mixed vintages and P6's 43,634 px page remain. The missing gates are coherence-age assertions and whole-viewport/raw-token audits, not more component snapshot tests.

## Final severity order

1. **P2 — Critical, confirmed**
2. **P3 — High, confirmed**
3. **P1 residual mixed-vintage/freshness defects — High, original framing overstated**
4. **P6 — High/P1, confirmed and under-severed**
5. **P4 — High roadmap blocker, overstated as a current live defect**
6. **P5 — no independent defect; upstream/copy follow-up only**
