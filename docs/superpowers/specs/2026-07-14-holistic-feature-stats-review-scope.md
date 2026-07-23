# Holistic Feature / Stats Review — Scope

- Status: DRAFT scope for a David-directed research initiative. Cockpit-led (Gemini = football/stats lead; Codex = leakage/technical guardrails; Claude = synthesis + repo grounding). No model change ships from this doc — it produces a graded candidate map for David.
- Author: Claude Code · 2026-07-14
- Source directive: David, 2026-07-14 (verbatim): "also reconsider them, in fact don't rule out other stats we may have overlooked or ruled out too soon. take a step back and look holistically at the stats we could use."
- Context: arose from Studio 001 G4 (target share / YPRR display). David expanded it from "these stats" to a holistic audit of the whole feature space.

## What this is (and is not)

This is a **descriptive candidate map**, not a model change. It inventories every stat we could plausibly use, grades each on real dynasty predictive signal, checks it against the hard leakage wall, and names its capture path and the validation it would need. Any actual model-input change remains human-gated and requires pre-registered validation (constitution: model inputs are expanded only by deliberate, gated promotion) — this review only produces the ranked candidate list David chooses from.

## Immovable constraints (stated up front so the review doesn't waste cycles)

- **Market-data leakage wall is hard.** KTC / ADP / FantasyCalc / DynastyNerds never become model inputs. They stay display-only overlays. Not in scope for reconsideration.
- **Engine A / Engine B separation holds unless explicitly rethought.** Pre-NFL/college metrics (dominator, breakout age, draft capital, speed score, college target share) live in Engine A by design; "should X move to B" is a legitimate question but must justify crossing the boundary, not assume it.
- **Display vs. model input are different asks.** Almost anything can be *displayed* (subject to No-Verdict + lane isolation). The high bar is *model input*. Each candidate is graded for both.
- **Aging curves stay fitted-continuous; RAS stays risk/context** — unless this review's backtest evidence earns a change, which then needs its own validation.

## The four buckets to audit

**Bucket 1 — Currently excluded for statistical reasons (revisit as inputs).**
- `target_share_nfl`, `air_yards_share`: excluded for multicollinearity (r=0.978 / 0.949 with `weighted_opportunity`; `tests/test_engine_b_contract.py:154-160`). Question: is `weighted_opportunity` the right composite, or would a decomposed set (with regularization / a chosen orthogonal subset) predict better? Grade the tradeoff.

**Bucket 2 — Engine-A-only metrics (revisit the boundary).**
- `dominator_rating`, `receiving_yards_share`, `breakout_age`, `speed_score`, college `target_share`, draft capital (`pick`/`round`/`draft_year`). Question: does any carry residual NFL-production signal that justifies a *governed* presence in Engine B (not leakage, not double-counting)?

**Bucket 3 — Uncaptured but reachable from approved sources (new signal).**
- nflverse / NGS-class we don't yet use: separation, cushion, aDOT, YAC-over-expected, target quality, pressure rate / time-to-throw (QB), route participation (already partially available), red-zone / high-value touch share, snap-share trend shape. Question: which carry dynasty (not just redraft) predictive signal, and what's the capture cost?

**Bucket 4 — Locked/prior rulings possibly ruled out too soon.**
- RAS (risk/context-only by ruling): has anything changed that warrants a backtest for positive lift? Aging-cliff hard ages (warnings-only). Anything in the archive ruled out before we had the data to test it.

## Per-candidate grading (the output schema)

Each candidate stat gets a row: `name · bucket · source/capture path · dynasty-signal hypothesis (with evidence basis) · redraft-vs-dynasty distinction · leakage check (pass/fail) · collinearity risk vs existing features · display-ready? · model-input bar (what validation it would need) · evidence grade (A/B/C) · recommended next step`.

## Lane roles

- **Gemini (lead):** the football/stats substance — which stats matter for dynasty, why, current-source evidence, the dynasty-vs-redraft distinction, what a sharp manager would weight. Prioritizes the candidate list.
- **Codex:** leakage/technical guardrails — for each candidate, is it obtainable without market leakage, does it double-count an existing feature, what's the real capture/retention cost, what validation gate applies.
- **Claude:** repo grounding (what's already captured/excluded and why), synthesis into the graded map, cockpit routing, and the David-facing brief.

## Falsification seeds

1. Does "reconsider target share as an input" quietly reintroduce the collinearity the exclusion prevented? (The grade must confront the r=0.978, not wish it away.)
2. Does any Bucket-3 stat smuggle future-season or market information? (Leakage check is mandatory, not optional.)
3. Redraft-vs-dynasty: a stat with strong single-season signal but no multi-year durability is a redraft feature, not a dynasty one — the grade must separate them (constitution: never conflate dynasty and redraft).
4. Does adding N features risk overfitting the small NFL cohort? (Feature-count vs sample-size discipline; the Ridge models are deliberately lean.)

## Technical guardrails (Codex, binding on the candidate map)

1. **Correlated families are substitutes, not additive.** Known high correlations: `target_share_nfl`/`air_yards_share` vs `weighted_opportunity` (r=0.978/0.949), `route_participation` vs `snap_share` (r=0.785) — `engine_b_contract.py:117-123`. Any revisit is a WOPR-vs-components or residualized-family **bakeoff**, never adding the correlated members together. A candidate row that proposes a raw target/air pair *alongside* WOPR, or route participation *alongside* snap share, is auto-flagged.
2. **Capture provenance is mandatory.** NFL routes/YPRR/TPRR already derive from nflverse PBP+participation (`feature_assembly.py:210-232`); any capture needs immutable source/version/as-of snapshots (replayable). NGS tracking fields (separation, cushion, etc.) additionally need license clearance, historical replay, identity resolution, and retention approval — flag any NGS candidate lacking replayable historical snapshots.
3. **Engine-A college priors do not migrate wholesale into B.** They risk duplicating cold-start prior/production signal; CFBD needs deterministic silver joins at 99% coverage; college YPRR stays governed/paywalled. Raw college-to-B migration is auto-flagged.
4. **Selection methodology (small-cohort discipline).** Feature selection happens *inside* training folds with the final temporal folds untouched; the map reports coverage/missingness and per-position sample sizes. Model-card context is only ~43–49 QB and ~30–35 TE rows per fold — the lean Ridge models do **not** license a broad shopping list. Feature-count vs sample-size is a first-order constraint, not a footnote.
5. **Validation gates per engine.** Engine A: CFBD 3% MAE + 3/4 LOOCV + TE non-regression. Engine B: a distinct David-ratified **pre-registered temporal bakeoff** with leakage/collinearity/stability tests. RAS stays context/risk; market stays prohibited. No candidate advances to an input without clearing its engine's gate.

## Output

A graded candidate map (`docs/…/holistic-stats-candidate-map.md`) delivered to David: the ranked list, each row's evidence grade, and a recommended shortlist of "worth a pre-registered validation." David chooses what, if anything, advances to a model-change cycle.
