# H2 Manager-Voice Doctrine — Claude's Draft (cockpit-round synthesis)

**Date:** 2026-07-05 · **Author:** Claude (implementation lead) · **Status:** v3 — **RATIFIED BY DAVID as the PRODUCT ROADMAP, 2026-07-06** ("use elite not stud, and choose a special vocabulary for the top 1%. otherwise this looks good... THIS IS NOW OUR PRODUCT ROADMAP"), with David's rulings recorded in §10 and the airtight execution sequence in §10.7. Derivation-gated items (canonical field pin, youth-threshold derivation, constitution amendment text) remain individually David-gated actions. v1 authored independently before reading any Gemini artifact; v2 integrated the adversarial cockpit round (review log §11; citations §12).
**Trigger:** David's directive — the no-directive rule "can chill out a little on the frontend"; a way-higher-PVO player can be called a stud; elite cohorts can be called elite; the frontend should surface patterns, cohorts, trends, opportunities, weaknesses, threats; useful and enjoyable UI/UX; manager language, never backend language.
**Research base (three independent web-research lanes, run 2026-07-05, full citations in the session ledger):** (L1) premium data-product label practice — FICO, Morningstar, PFF, Baseball Savant, Whoop/Oura/Garmin, chess.com, Levels.fyi, Wirecutter/CR, Spotify Wrapped, Bloomberg, Carbon/Polaris; (L2) dynasty manager lexicon — KTC, DynastyGM/Nerds, DLF, FantasyPros, PFF, Footballguys/Harstad; (L3) label psychology — Kent/ICD-203 estimative language, IPCC/Budescu calibrated vocabulary, van der Bles/Spiegelhalter uncertainty-and-trust, Teigen & Brun label directionality, automation bias, Yelp/credit-rating boundary-cliff economics, traffic-light color semantics.

## 1. My committed POV: split the No-Verdict Line, don't breach it

The current constitution conflates two different prohibitions:

1. **The tool must never decide for David** — no buy/sell/accept/cut/start imperatives, no recommended action, no hidden action ordering. This is the real No-Verdict core. It STAYS LAW. Nothing in David's directive touches it (Codex's read concurs), and the research is emphatic that this line is what separates trusted data products from hype (L2's "verdict smuggling" failure mode; L3's automation-bias findings).

2. **The tool must not use quality words** ("avoid subjective static tier labels — 'Elite', 'Bust', 'Starter Depth'"). This clause treats every quality word as inherently subjective. The research says that is wrong **when — and only when — the word is bound to a disclosed numeric definition**: PFF publishes "Elite = 90+" over a normalized distribution and is the most-cited grading house in football; FICO's "Exceptional = 800–850" never renders without its range; the IPCC's "very likely" is a ratified alias for a disclosed probability band. A bound label is not a judgment smuggled into a description — it is a *rendering of the number in the reader's native dialect*. Banning it doesn't make DG more honest; it makes DG less legible, and legibility is a form of honesty.

So the amendment is narrow: **imperatives stay banned; a small, David-ratified, numerically-bound quality vocabulary becomes legal.** The label inherits every honesty obligation the number already carries — and adds new ones (§4).

One structural honesty move makes the whole thing safe: **every DG label is a claim about the model's output, never about football ground truth.** "Elite" means "the model values him in its own top band" — a statement that is TRUE regardless of whether the model is right about football. The receipt carries that framing ("by DG model value · model grade: experimental"). This is Morningstar's stars-vs-medals separation applied to us: our labels are backward-looking-descriptive of the model state; a forward-looking "this will work out" layer does not exist and cannot exist until Gate-4 earns it. L1's spectrum rule: *the more unvalidated the model, the more descriptive the labels must stay* — quality tiers now; anything stronger only after pre-registered validation.

## 2. Three registers (where each kind of language lives)

- **Terminal register** (tables, rows, chips, charts — most of the app): calibrated labels + numbers, Savant-sterile discipline. Word and number always travel together.
- **Narrative register** (the daily open masthead, season recaps, milestone moments): the Wrapped lesson — one curated headline per view, David's roster as protagonist, warm storytelling, screenshot-shaped — bounded by the §5 materiality/anti-cherry-pick rule. Narrative copy uses the same calibrated ladder words as the terminal (David-ruled 2026-07-06: no separate narrative dialect; "stud" removed).
- **Receipt register** (title attributes, receipt panels, developer zone): exact terms, raw values, hashes, thresholds, model grade, denominators. Unchanged from the current voice guide.

Delight lives in the narrative layer; trust lives in the terminal layer; they never blend (L1 rule 10).

## 3. The lexicon zones

### Zone A — stays banned everywhere (the No-Verdict core)
- Imperatives and transaction directives: buy/sell/hold-as-command, accept/reject, add/drop/cut/start/sit-as-command, "should", "must", "do not", "safe to", "recommended", "target him". **Enforcement is phrase/context-aware (Codex must-not-omit #7): action-order VERBS are banned; neutral transaction NOUNS and descriptive phrases ("trade partner", "waiver pool", "the trade shape to inspect", "buy-low window" as a market-fact noun) remain legal when not directive.**
- Conviction words with no falsifiable content (L2 failure mode 4): "smash", "must-start", "league-winner", "no-brainer".
- Negative identity labels on noisy signals: **"bust" stays banned** (the Garmin-"Unproductive" lesson — negative-valence labels on low-confidence data are the highest-risk quadrant; risk is expressed as cohort/trajectory facts instead: "historical age-34 WR cohorts show elevated decline").
- Red/green quality coloring and stop/go iconography (L3: color IS a command; constitutionally already banned — reaffirmed).
- Hidden action ordering: any sort/rank that functions as "do this first" without a disclosed basis.
- Fabricated certainty: labels on stale/degraded/low-coverage data (labels suppress BEFORE numbers do — §4.5).

### Zone B — calibrated quality ladder (NEW — legal with bound definitions)
A single product-wide ladder, distribution-pinned so scarcity is structural (PFF normalization + Oura's "100s are rare"):

| Label | Bound definition (ladder DAVID-RATIFIED 2026-07-06; cuts remain tunable by David at ratified checkpoints) |
|---|---|
| **Generational** | top 1% of model value within position (percentile ≥ 99) — the apex word, **DAVID-RULED 2026-07-06**; scarce by construction (~1 player per position pool). Honesty rider: colloquially "generational" implies a career-arc forecast, so the bound definition + receipt anchor it strictly to CURRENT model value ("top 1% of model value at WR, today — by DG model, grade: experimental"), never a career prediction |
| **Elite** | percentile 95–99 (David-ruled: "elite", not "stud" — "stud" appears nowhere in the product) |
| **Cornerstone** | Generational-or-Elite AND age ≤ position youth threshold — thresholds EMPIRICALLY DERIVED from our fitted aging curves, or David-taste-ratified with the basis disclosed as taste; any interim numbers are provisional examples only (the rookie-prior v1→v2 folklore-scalar lesson) |
| **Starter tier** | percentile 60–95 (role-shaped, self-explaining — PFF's grammar) |
| **Depth** | percentile 25–60 |
| **Replaceable-range** | below 25 — rendered as the percentile phrase, never as a scarlet letter; no badge, number only |

**Canonical basis field (Codex technical pin, cockpit-converged):** quality labels bind to ONE canonical within-position model-value percentile field (e.g. `model_value_position_pct`) computed over the active starting population at the position. The anchor scalar (xVAR-derived vs DVS-derived) is pinned from producer semantics by Claude/Codex before implementation — the lexicon must NOT bind to ambiguous legacy names (`dvs_pct` currently doubles as `xvar_percentile_position` in `universe_pvo_batch.py:95`). Source-verified definitions: `dynasty_value_score` = `projection_2y / position_p90_benchmark × 100`, clamped 0–100, PLAYER-LEVEL and roster-independent (`pvo_assembler.py:389-407`, Codex-confirmed); xVAR = value above replacement starter. A "roster share/concentration" reading of DVS is WRONG — that mis-gloss also lives in voice guide v0.3 §5 (`2026-07-05-h2-dg-voice-guide-design.md:80-83`) and is added to the amendment surface (§6.8).

Rules: the ladder is ONE taxonomy used identically everywhere; no synonyms with overlapping bands; bands re-center on the model's own distribution each refresh; threshold changes are versioned, David-gated events (mirrors the frozen-model ruling).

**The "stud" question — RULED (David, 2026-07-06): "use elite not stud."** "Stud" joins Zone A (it appears nowhere in the product); the ladder words are the only quality vocabulary in every register. This also lands on the research-preferred side: L3 flagged "stud" as directional (it evokes action in a way the positional ladder words don't). Historical note: v2 had recommended a register-split alias; superseded by David's ruling.

### Zone C — trajectory and market movement
- The canonical mover grammar, adopted verbatim from the industry's most-loved trend UX (KTC): **direction + magnitude + window + lane basis** — "+485 · 30 days · market". Lane always named; a market move never wears a model label (existing wall, reaffirmed).
- Trajectory words over REAL PIT series only (Hard Right Edge holds): "riser", "faller"; "surging/free-fall" only at ratified magnitude cuts. No trend language over pending series.
- Standing recency caveat on short windows; 30-day default (L2: the mover feed is the bias engine — our antidote is structural).
- **"Market disagreement"** is the divergence noun (descriptive distance), never "market is wrong" (unvalidated-edge discipline holds).

### Zone D — roster structure, opportunities, weaknesses, threats
David's SWOT ask, rendered as facts with mechanisms:
- Structure: "thin at WR — 2 startable by model value vs league median 4"; "deep at RB". Counts + comparison basis, always.
- Opportunity = **a mispricing or capacity fact quoted with its window**, in price language (L2 rule 1): "model values him WR8; market prices him WR14" — never "go get him".
- Threat/weakness = cohort and structural facts: aging-cliff warnings (constitutional ages, already law), "starting lineup depends on 3 players over their position's cliff age".
- Posture words (contender/rebuild) render only as David's own declared posture echoed back, or as disclosed-basis descriptive aggregates — the tool never assigns David a strategy.

## 4. Label mechanics (the honesty machinery — every rule research-anchored)

1. **Word + number, always, in comparable weight.** No chip without its percentile adjacent (NC "Know the Score"; Budescu: word-only displays are misread even WITH a published mapping; tooltip-only disclosure is insufficient).
2. **Denominator + vintage on the receipt.** "top 5% of 84 Superflex-relevant WRs · as of Jul 5" (chess.com named-population pattern; Levels.fyi n-gating — cohort labels need a sample-size floor, no "elite cohort" on n=3).
3. **De-cliffed boundaries.** The percentile is always visible so 89.9 vs 90.2 never reads as categorically different (Yelp half-star pathology); when a value's fold-CI straddles a band edge, the chip carries a straddle marker ("Elite — at the boundary"). No label strobing: day-over-day flapping across a cut renders as the trajectory fact, not oscillating badges. **Hysteresis rule (cockpit-converged recommendation):** raw numbers update immediately; a badge changes only after the player holds the new band ≥3 consecutive daily captures OR clears the cut by ≥2 percentile points.
4. **Uncertainty rides as numeric range, not verbal hedge** (van der Bles: ranges cost ~no trust; hedging words do). The quality-vs-confidence split renders in one line when needed — the industry's own "Tier 1 on ability, Tier 2 on peace of mind" pattern maps to our fold-CI.
5. **Labels degrade before numbers.** Stale/degraded/low-coverage substrate suppresses badges to percentile-only with the standard caveat; a label is a luxury of healthy data (extends the existing stale-desaturation law).
6. **Model-claim framing in every receipt**: "by DG model value · model grade: experimental · accuracy record: Accuracy Tracker" — the label links to the credibility room (L3's overreliance remedy; our Realized-Outcome loop is the built-for-this receipt).
7. **Epistemology separation** (Morningstar): model-quality labels and market-price observations never share a vocabulary or a visual treatment; any future forward-looking layer would need its own visually distinct system and a validation track record first.
8. **Neutral chip visuals**: labels render in ink/neutral treatments (Polaris one-word badge discipline; Carbon ≥3-of-4 channels, never color-alone); the existing no-verdict-hue law is unchanged.
9. **One lexicon module** (`frontend/src/lib/lexicon.ts` growing out of `copy.ts`): every label word renders ONLY through it; thresholds live there, versioned; a scan bans lexicon words rendered outside it. The voice guide's vocabulary map (v0.3) merges in as the system-noun half.
10. **Anti-Goodhart tripwire**: if any human-tunable input starts bunching players just above a cut, that is a defect finding (EU energy-label bunching lesson) — a diagnostics-zone check, not a David-facing surface.

## 5. Useful and enjoyable (the product half David asked for)

- **Screens organize around the six manager questions** (L2): What changed? Is this trade fair? Who to target and with whom? Where am I thin? Contend or rebuild? Start/sit-adjacent context. Not around model internals. DynastyGM's most-loved trait is that every view is *my roster against my league* — DG already has the sync; every surface leads with David's assets.
- **The daily open gets its Wrapped moment**: one curated headline insight in the masthead, receipt-backed, then the sterile feed below. **Anti-cherry-pick rule (cockpit-converged):** the masthead leads with the most MATERIAL high-confidence insight — a major roster exposure or cliff threat outranks a positive superlative; positive delight is allowed but can never hide the most material pressure point.
- **Freshness is a feature users love** (KTC's "values feel alive") — our tape already leads with it; keep receipts one tap away, not inline noise.
- **Delight at moments, not pages** (impeccable product register): capture-streak milestones, first-finalized-week celebration (~Sept), draft-day. Quiet days stay honest but warm ("Values held steady overnight — systems synced.").

## 6. Amendment surface (exact, David-gated)

1. **Constitution 00, No-Verdict Line, "Ranks and tiers" bullet** — replace "avoid subjective static tier labels ('Elite', 'Bust', 'Starter Depth')…" with: tiers/labels are legal ONLY as entries in the David-ratified calibrated lexicon, each bound to a disclosed numeric definition over a named population, rendered word-with-number, degrading with data health; imperative/directive language remains banned per the preceding bullet. (Proposed amendment text to be drafted for David's ratification in the cockpit round.)
2. **`frontend/src/shell/banned_vocabulary.json`** — remove standalone bans "elite", "starter", "depth" (they become lexicon-gated); **keep "bust"**; keep ALL phrase bans (buy now / should accept / recommended action / must add…); "dynasty tier" phrase ban → superseded by the disclosed-basis ladder rule.
3. **`frontend/src/ui/ValueBandDivider.test.tsx`** (Codex-owned) — amend the /elite|bust|must-start|league winner/ ban: "elite" legal only with adjacent bound basis; "bust/must-start/league winner" stay banned.
4. **Reset spec seed 24** — already conditional ("without disclosed numeric basis") — reconcile wording to the lexicon rule.
5. **DN benchmark §3 translation row** — "ELITE DYNASTY ASSETS → value-band dividers with disclosed basis" becomes "→ calibrated lexicon labels with bound bands" (same mechanism, now with the ratified words).
6. **Voice guide v0.3** — merges into this doctrine as the system-noun translation half; its open xVAR/DVS question stays a David decision.
7. **New enforcement** (Codex REDs): lexicon-module single-source scan; chip-requires-basis; threshold-respecting render tests; staleness-suppresses-labels; sample-size floor for cohort labels; straddle-marker behavior; hysteresis behavior.
8. **Voice guide v0.3 §5 DVS gloss correction** (`2026-07-05-h2-dg-voice-guide-design.md:80-83`) — "share of roster value / Dynasty Value Share" is wrong per producer source (`pvo_assembler.py:389-407`); corrects to "Dynasty Value Score (DVS)", exact gloss pending the canonical-field pin (§3).

## 7. Falsification seeds

1. "Elite" chip renders for a player below the ratified percentile cut → RED fails.
2. Any lexicon word renders outside the lexicon component (hand-rolled string) → scan fails.
3. Chip renders without its adjacent number/percentile → RED fails.
4. Badge renders while the substrate is stale/degraded → must suppress to percentile-only + caveat.
5. Cohort label on a sub-floor sample (e.g., n<8) → RED fails.
6. Fold-CI straddles a band edge without the straddle marker → RED fails.
7. A label word concatenated with an action ("Elite — trade for him") → phrase bans still fail it.
8. Market-lane data wearing a model-quality label (lane bleed) → RED fails.
9. A "riser/faller" over a pending/gapped series or without window+magnitude+lane → RED fails.
10. Red/green or stop/go treatment on any quality chip → token guards fail.
11. Day-over-day label strobing across a boundary renders as flapping badges instead of a trajectory fact → RED fails.
12. "Bust"/"must-start"/"league-winner"/"smash" anywhere in rendered copy → linter fails (unchanged).

## 8. Steelman (the strongest case against, answered)

L3's steelman, faced squarely: (1) evaluative words carry intrinsic direction no disclaimer removes (Teigen & Brun); (2) disclosed mappings don't fully transfer to readers (Budescu: 28–54% alignment even with inline ranges); (3) labels manufacture boundary cliffs; (4) automation bias over-follows confident labels; (5) a confident label that visibly busts costs disproportionate trust (algorithm aversion) — and our model is unvalidated.

Response: every documented failure case is a *word-primary, number-hidden, direction-loaded, boundary-cliffed* design. This doctrine's safe harbor is the negation of each: number-primary, mapping-inline, non-directional ladder words (role/distribution-shaped), de-cliffed boundaries, staleness-degrading, model-claim-framed, single-user-ratified vocabulary. And the residual risk (Budescu's minority who misread anyway) is why the label is never the only load-bearing element of any surface — the number is always there. The single-user context is the final mitigation: the reader and the ratifier of the dialect are the same person.

## 9. The insight-engine frame (David's controlling direction, relayed by Codex)

This doctrine is the **presentation grammar** for the insight engine: data → insight → the form that reflects that insight (David's controlling direction — the backend continuously hunts for competitive-edge patterns: performance, age, league-manager behavior, positional, market disagreement, roster construction, trend changes, threats, weaknesses, leverage pockets, emerging cohorts). The zones and registers above are precisely the vocabulary insights render in — a cohort insight renders as a calibrated cohort label + members + basis; a market-disagreement insight renders as two lane prices + distance + window; a roster-structure insight renders as counts vs league comparison; a trend insight renders as direction + magnitude + window + lane over a real PIT series.

**Insight validation ladder (cockpit-converged recommendation):** Hypothesis → (out-of-sample test) → Provisional → (David approval) → Validated. Visible exploratory states are allowed with three bounds (three-way concurred): (i) they live in a dedicated insights area or the narrative register — never as chips inside terminal data rows; (ii) an unvalidated pattern may never wear a calibrated quality word; (iii) materiality/anti-cherry-pick applies — exploration is not license to spam. **The ladder is fully separate from decision-grade: promotion to "Validated" NEVER flips `decision_supported` — that remains exclusively the pre-registered Tier-2/Gate-4 path; the two ladders must not be conflatable.**

Guardrails carried upstream into the insight-discovery workstream: (1) **insight discovery is analysis over frozen model outputs + captured data — it never becomes in-season model auto-tuning or parameter drift** (the frozen-model constitution ruling binds the engine too); (2) **insight confidence is accrual-honest** — pattern claims that need outcome history (trend edges, market-disagreement validation) inherit the ~Dec 2026 accrual gates and render as hypotheses with receipts until earned. The insight-discovery workstream itself (backend producers that hunt for new patterns) is a separate David-gated program after the frontend reform lands.

## 10. DAVID'S RULINGS (2026-07-06) + the airtight execution sequence

**Ruled 2026-07-06** ("use elite not stud, and choose a special vocabulary for the top 1%. otherwise this looks good... THIS IS NOW OUR PRODUCT ROADMAP"):

1. **The lexicon ladder — RATIFIED** with the top-1% rung: **Generational** (≥99) / Elite (95–99) / Cornerstone (Generational-or-Elite + young) / Starter tier / Depth / replaceable-range. Cuts tunable by David at ratified checkpoints.
2. **"Stud" — REJECTED**; "Elite" everywhere; no separate narrative dialect. "Generational" is David's chosen apex word (overriding Claude's "Franchise" proposal).
3. **Roster posture — accepted as recommended** (Option A): declared posture echoed + descriptive disclosed-basis overlay; the tool never assigns a strategy.
4. **Metric vocabulary — accepted as recommended** (Option A bridge headers), glosses shipping only after the canonical-field pin (§3).
5. **Cornerstone youth thresholds — accepted as recommended** (Option A): empirically derived from fitted aging-curve/cohort data; taste-ratification remains David's fallback with the basis disclosed as taste.
6. **Sequencing — verified airtight below (§10.7), per David's directive** to double-check it.

### 10.7 The execution sequence (dependency-verified, each step David-gated)

**Step 0 — immediately unblocked (sequencing fix from the airtight check):** the **Task-5 daily-open preview**. Its copy uses ZERO quality-label vocabulary (tape prose, signed deltas, quiet states — verified), so it is legal under current AND amended law and depends on nothing in this reform. The v2 draft had placed it after the enforcement REDs — an unnecessary serialization, now corrected. Preview → David's commit word → the reset package closes. Admin rider: David's word on tracking `PRODUCT.md`/`DESIGN.md` and committing this roadmap document.

**Step 1 — the constitution amendment (law before enforcement):** Claude drafts the explicit 00 No-Verdict "Ranks and tiers" amendment text → full adversarial cockpit cycle (governance amendments REQUIRE it, 02) → David ratifies → commit. HARD ORDERING CONSTRAINT: no enforcement surface (banned_vocabulary.json, ValueBandDivider RED, seed 24, DN-benchmark row) may change before this lands — enforcement implements law; changing it first is silent reinterpretation.

**Step 2 — technical prerequisites (parallel with Step 1; no law dependency):**
 (a) canonical-field pin — Claude/Codex resolve the anchor scalar (xVAR- vs DVS-derived) from producer semantics and define `model_value_position_pct`-style exposure; **this pin also determines whether Step 3 needs a backend API slice** (if the canonical percentile is not already in the served DTOs, field exposure + OpenAPI/codegen is a Step-3 sub-task — hidden dependency surfaced by the airtight check);
 (b) Cornerstone youth-threshold derivation from the fitted aging curves (data analysis; Cornerstone activates only when this lands — the ladder ships without it, flag-gated);
 (c) voice-guide v0.3 DVS gloss bug fix (independent correction, any time).

**Step 3 — lexicon build (requires Steps 1 + 2a):** `lexicon.ts` module + badge primitive + enforcement REDs via full cockpit-TDD (Gemini framing → Codex RED → Claude GREEN): single-source scan, chip-requires-basis, hysteresis, staleness suppression, straddle markers, sample-size floor, lane separation — the §7 seeds become the RED contract.

**Step 4 — surface adoption (requires Step 3; one David-gated increment per surface):** daily-open narrative masthead moment first, then chips into the player atom (I3) and the I4 re-skins. STANDING HAZARD (named here so it cannot be missed later): any adoption touching the byte-pinned League Pulse / Trade Lab mitigation copy routes through a graduation-contract amendment cycle — never a casual copy edit (the verify-lock-release lesson).

**Step 5 — the insight-discovery workstream (after Steps 1–4; its own David-gated program + spec):** backend pattern-hunting producers under the §9 pipeline (Hypothesis → Provisional → Validated), frozen-model + accrual guards binding, `decision_supported` untouched by insight promotion, exploratory rendering under the three bounds.

Dependency audit performed: no cycles; nothing waits on anything it does not need; the two previously-hidden couplings (Step-0 preview falsely serialized behind REDs; Step-3's conditional API slice) are surfaced above.

## 11. Review log (cockpit round, 2026-07-05 — positions quoted per the consensus-lock rule)

- **Claude v1**: independent draft from three research lanes; not derived from any Gemini artifact.
- **Gemini (PM lane, advisory)**: CONCUR on v1 structure; proposed resolutions on the open items → re-framed as recommendations after Claude's lane note. Contributed: hysteresis rule, masthead anti-cherry-pick, insight validation ladder, posture option A, provisional youth thresholds. Two Claude defects accepted (invented youth constants → curve-derived-or-taste-ratified; "age-cliff discount applied by market" causal fabrication → factual co-render). One VOIDED repo-state claim (DVS = "roster share/concentration" presented as verified — wrong per producer source) — accepted + corrected; artifact re-verified clean.
- **Codex (technical lane)**: confirmed the DVS producer read (`pvo_assembler.py:389-407`; voice-guide bug at `...voice-guide-design.md:80-83`); pinned the canonical lexicon field requirement (`model_value_position_pct`-style, no binding to ambiguous legacy names); 9-item must-not-omit list — all integrated (insight-engine doctrine §9; frozen-model guard §9; DRAFT status; DVS correction §3; canonical field §3; decision_supported separation §9; phrase/context-aware enforcement §3 Zone A; youth thresholds Choice 5; narrative materiality §5). No additional blocker; awaiting v2 defect pass.
- **David steering during the round**: nothing is finalized — all drafts/proposals; open slots preserved; Gemini pace correction; independence directive to Claude.
- **v2 final defect pass**: Gemini — no findings. Codex — no blocking finding; two non-blocking cleanups applied (header §-reference fix; self-contained citation appendix §12).
- **v3 (2026-07-06)**: DAVID RATIFIED as the product roadmap with rulings — elite-not-stud; top-1% word = "Generational" (David's word, overriding Claude's "Franchise" proposal; honesty rider added anchoring it to current model value); recommendations on posture/vocabulary/thresholds accepted; sequencing double-checked per David's directive → two fixes surfaced (Task-5 preview unblocked to Step 0; Step-3 conditional API slice named).

## 12. Citation appendix (major research anchors, self-contained for future audit)

**Calibrated-vocabulary precedents:** Kent, "Words of Estimative Probability" (CIA Studies in Intelligence, 1964) — cia.gov/resources/csi/studies-in-intelligence/archives/vol-8-no-4/words-of-estimative-probability; ICD 203 Analytic Standards 7-band vocabulary; IPCC calibrated language + Budescu et al. (Nature Climate Change 2014, nature.com/articles/nclimate2194; Climatic Change 2012) — word-only labels misread regressively, word+range narrows but never fully; Mandel & Irwin (Earth's Future 2021) — number must be primary.
**Uncertainty & trust:** van der Bles, Spiegelhalter et al. (PNAS 2020, pnas.org/doi/abs/10.1073/pnas.1913678117) — numeric ranges cost ~no trust; verbal hedges do.
**Label directionality:** Teigen & Brun (OBHDP 1999, pubmed.ncbi.nlm.nih.gov/10527815) — evaluative words carry intrinsic action direction (the basis for excluding directional quality words from the ladder; consistent with David's elite-not-stud ruling).
**Boundary-cliff economics:** Anderson & Magruder (Economic Journal 2012) + Luca (HBS) on Yelp half-stars; BIS Papers No 72 on rating-cliff herding; EU energy-label bunching (Energy Economics 2025) — the de-cliffing + anti-Goodhart rules.
**Automation bias / algorithm aversion:** Dietvorst, Simmons & Massey (2015; Management Science 2018); Microsoft overreliance-on-AI review (2022) — labels over-followed; visible confident failures cost outsized trust.
**Color semantics:** traffic-light red/green = stop/go command activation (IJBNPA 2015; fMRI PMC7019506) — no red/green on quality chips.
**Product precedents:** FICO band grammar (myfico.com/credit-education/credit-scores); Morningstar stars-vs-medals + Analyst-Driven %/Data Coverage % (advisor.morningstar.com Medalist explainer; WSJ 2017 critique) — separate epistemologies, label carries its own receipt; PFF grade bands "Elite = 90+" over normalized distribution (pff.com/grades); Baseball Savant percentile grammar (baseballsavant.mlb.com/leaderboard/percentile-rankings); Whoop/Oura capability-framing + scarcity ("100s are rare"); Garmin "Unproductive" backlash + orthosomnia (PMC11592250) — negative labels on noisy signals; chess.com named-denominator percentiles; NC "Know the Score" side-by-side mandate (choicesmagazine.org/2005-2/safety/2005-2-02.pdf); Spotify Wrapped narrative register; Bloomberg non-semantic amber (bloomberg.com terminal color-accessibility story); IBM Carbon status-indicator ≥3-of-4 channels; Shopify Polaris one-word badges.
**Dynasty lexicon:** KTC FAQ ("at best a gut check"; riser/faller + window grammar — keeptradecut.com/frequently-asked-questions); DLF Cornerstone Rankings; FantasyPros tier copy ("Tier 1 on ability, Tier 2 on peace of mind"; soft-boundary admissions); PFF Dynasty Stock Watch; Harstad "Dynasty, in Theory" #36/#40/#41 (footballguys.com) — heuristics over projections, confidence is the unreliable variable; DynastyGM league-sync reviews (justuseapp.com).
