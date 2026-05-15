# Dynasty Genius — Phase 12 Research Brief, Merged

Prepared May 2026. Source inputs:

- `docs/strategies/Phase 12 Research.md`
- `docs/strategies/Dynasty Genius_ Phase 12 Research Brief.md`
- two downstream synthesis reviews supplied in session

## 1. Executive Recommendation

**Recommended Phase 12 theme: Operational Backtest Artifacts + Trust Surface v2.**

Phase 12 should convert the Phase 10/11 harness from a working validation system into an operational trust layer. The immediate work should be:

1. Run the first operational backtest artifact generation for QB, RB, WR, and TE.
2. Persist model cards, fold reports, calibration data, market-comparison ledgers, gate evaluations, and subgroup diagnostics.
3. Extend the Trust Surface so it serves those artifacts clearly and read-only.
4. Explicitly document what is decision-grade, what is experimental, and what remains unvalidated.

This is the best next phase because it is high impact, low risk, and directly consumes the work just merged in Phase 10/11. It adds no model inputs, no market-derived features, and no new predictive claims. It turns backtesting into visible product evidence.

Two later synthesis reviews argued for a "two-act" Phase 12 that generates artifacts first and then implements DVS. The useful part is the dependency order: DVS needs artifacts as its calibration substrate. The risky part is treating that as implementation approval. This merged brief keeps DVS as a design/guardrail deliverable until the first operational artifacts prove the calibration base is sound.

**Backup option A: Dynasty Value Score design and calibration.**

The unified Dynasty Value Score is architecturally important, but it should not be Phase 12 implementation. It combines Engine A prospect scores and Engine B active-player forecasts into one cross-position value currency. That requires calibration, uncertainty handling, and validation artifacts that do not yet exist operationally. Shipping DVS before the trust artifacts would launder model uncertainty into a single number.

**Backup option B: TE diagnosis and remodel.**

TE remains the live model failure point. It deserves a dedicated diagnostic phase, but the first operational artifacts should identify whether TE fails because of rank correlation, calibration drift, role heterogeneity, sample size, touchdown noise, or market-comparison weakness. Without that diagnosis, a TE remodel risks guessing.

**Explicitly deferred:**

- RB feature expansion. Weighted opportunity and high-value touches are promising, but new features should wait for baseline artifacts and backtest gates.
- Isotonic or Platt-style calibration as a deployed layer. First measure miscalibration.
- Divergence/G4 signal promotion. Native FC snapshots and a persistent market ledger must mature first.
- Cross-position DVS production values. Keep `dynasty_value_score` guarded or null until a validated bridge exists.

## 2. Why This Beats the Unified-Score-First Plan

The DVS-focused report correctly identifies a real architectural need: Dynasty Genius eventually needs a single comparable value currency. Engine A emits prospect scores on a 0-100 style scale, while Engine B emits two-year PPG forecasts. Trade Lab, Roster Audit, and League Pulse will ultimately need a unified score.

The issue is sequence.

Phase 10/11 created the harness, but the first operational artifacts still need to be generated and reviewed. Until then, the system does not know:

- which positions pass which gates on current operational artifacts;
- how calibrated the PPG forecasts are by decile;
- where TE breaks;
- whether market-comparison folds are populated enough for G3;
- what the disagreement ledger says about model-vs-market cases;
- how confidence intervals should be exposed to decision surfaces.

The unified-score work should therefore be treated as a **Phase 13 candidate** or as a **Phase 12 design appendix**, not the core Phase 12 build. Its technical details are valuable, but the governance-safe order is:

1. Generate evidence.
2. Expose evidence.
3. Diagnose weak points.
4. Then calibrate/normalize into a single value score.

## 3. Phase 10/11 Implications

Phase 10/11 merged the core trust machinery:

- `WalkForwardDriver.run()` with four expanding-window folds;
- Ridge refit per fold with fixed alpha by position;
- Kendall tau-b, Spearman rho, RMSE, MAE, BCa intervals;
- market snapshot store and community CSV ingest;
- NDCG@12/@24 model-vs-market comparison;
- promotion gates G1-G4;
- `BacktestResult` persistence;
- `GET /api/trust-surface/{position}`;
- `scripts/run_backtest.py`.

That creates capability, not yet the final product evidence. Phase 12 should be the operationalization layer that makes the harness speak.

### Required First Operational Artifacts

For each position, Phase 12 should generate and persist:

- **BacktestResult JSON**: canonical per-position artifact already supported by Phase 10/11.
- **Per-fold prediction ledger**: player_id, position, fold, feature season, predicted PPG, realized outcome, residual, rank, and caveats.
- **Calibration report data**: decile bins, predicted mean, observed mean, residual distributions, and reliability-style plot inputs.
- **Rank report**: Kendall tau-b, Spearman rho, confidence intervals, rank-IC by fold and pooled.
- **Market-comparison ledger**: model rank/value, market rank/value, source, snapshot date, NDCG contribution, and realized outcome where available.
- **Gate evaluation report**: raw G1-G4 metrics, pass/fail/deferred status, grade, and promotion justification.
- **Subgroup slices**: age buckets, draft-capital buckets where available, prediction sample size, and role/position buckets.
- **Model cards**: one per position using a model-card style structure.
- **TE failure card**: explicit experimental status and quantitative failure mode.

### Decision-Grade Preconditions

Before any downstream surface claims decision-grade confidence, Phase 12 must verify:

- QB/RB/WR gate status from operational artifacts, not assumed historical summaries.
- TE remains experimental unless it passes the same promotion gates.
- Market comparison is sufficiently populated; unavailable market data must remain `deferred`, not false confidence.
- Calibration is described separately from discrimination/rank correlation.
- The Trust Surface explains limitations and does not imply "beats market" unless G3/G4 evidence supports it.

## 4. Candidate Phase 12 Options

| Option | Goal | Impact | Risk | Dependency readiness | Recommendation |
|---|---|---:|---:|---:|---|
| Operational artifact generation | Produce the first durable validation outputs | Very high | Low | Ready | **Phase 12 core** |
| Trust Surface v2 | Serve artifacts, model cards, caveats, gates | Very high | Low | Ready | **Phase 12 core** |
| Automated backtest reporting | Make fold/gate/calibration reports reproducible | High | Low | Ready | **Phase 12 core** |
| Passive divergence ledger | Store model-vs-market disagreement substrate | Medium-high | Low | Mostly ready | **Phase 12 stretch** |
| DVS design | Specify cross-position value currency | High | Medium | Needs artifacts | Design appendix only |
| Engine B calibration layer | Isotonic/percentile calibration | Medium | Medium | Needs diagnostics | Defer |
| TE diagnosis/remodel | Fix experimental TE | High | Medium | Needs failure artifacts | Defer to next model phase |
| RB feature expansion | Add WO/HVT/route/NGS features | Medium | High | Needs baseline | Defer |

## 5. Dynasty Value Score: Keep the Technical Work, Defer the Build

The DVS report's best contribution is its technical framing for future cross-position value normalization. Those ideas should be retained for the Phase 12 spec appendix or Phase 13 planning.

### Industry Context

Major dynasty value tools all convert ordinal or behavioral signals into cardinal trade scales:

- **KeepTradeCut**: crowd keep/trade/cut rankings, 0-9999 scale, separate Superflex and 1QB pools, strong sentiment/recency signal.
- **FantasyCalc**: actual executed trades, optimization-derived values, time-weighted recent trade behavior, useful for market price discovery.
- **DynastyProcess**: expert ranks transformed by value curves, transparent methodology, rookie-pick models using hit-rate/perfect-knowledge concepts.

Governance implication: these systems are useful market references, but they remain overlays. They must not enter Engine A or Engine B as predictive model features.

### Normalization Design Notes for Later

Bad approaches:

- pooled min-max scaling;
- pooled z-scores across positions;
- hardcoded Superflex multipliers without validation;
- using market value as the calibration target.

Better candidate approach, once artifacts exist:

1. Convert Engine B PPG forecasts into within-position calibrated percentiles using out-of-sample fold predictions.
2. Convert Engine A prospect outputs into rookie/prospect percentiles or expected PPG priors using historical rookie outcomes.
3. Anchor active value to league-format replacement levels before any cross-position comparison. Initial Superflex anchors should be treated as research defaults, not constants: QB24, RB36, WR48, TE12.
4. Evaluate isotonic regression as the first candidate calibration method because it preserves monotonic rank while mapping raw model outputs to realized percentile space.
5. Use a right-skewed cardinal transform only after calibration evidence exists. DynastyProcess-style value curves are a useful reference for why elite assets must not be made linearly interchangeable with depth pieces.
6. Preserve uncertainty bands and source labels in the PVO.

The DVS should probably expose both:

- `within_position_percentile`
- `cross_position_value_score`

The first is easier and safer. The second requires validation against market and realized outcomes.

If Phase 12 exposes any DVS-shaped field, the safest version is a **within-position percentile only**. A 0-10,000 cardinal score, exponential value curve, or Engine A/B blended trade currency should remain out of production until the calibration report and market-comparison ledgers justify it.

### Validation Paradigm for Future DVS

Future DVS work should inherit the Phase 10/11 validation language rather than inventing a new standard:

- discrimination: Kendall tau-b and Spearman rho;
- decision ranking: NDCG@12/@24 against realized outcomes and market baselines;
- calibration: decile reliability tables and residual distributions;
- stability: RMSE/MAE drift and Diebold-Mariano style comparisons where applicable;
- decision honesty: every strong recommendation needs a counter-argument field and an uncertainty label.

NDCG deserves special treatment because it better matches dynasty economics than a whole-board rank metric alone. Missing on the top 12-24 assets is more damaging than misordering replacement-level depth. The Trust Surface should therefore report rank correlation and NDCG together, not choose one as the single truth.

Future divergence validity should also stay gated. A Mann-Whitney style test and bootstrap confidence interval can be useful for model-vs-market flag validation, but only after the passive divergence ledger has enough observations. Until then, divergence is a disagreement to inspect, not an alpha claim.

### Prospect-to-Active Bridge

The useful idea from both reports is to treat Engine A as a prior and Engine B as an observed-performance model. A future bridge could:

- keep Engine A dominant pre-draft and during the earliest rookie window;
- blend Engine A and Engine B during years 1-2;
- use Engine B as primary once enough NFL usage exists;
- show "provisional rookie value" caveats during the transition.

This should not be built until the operational artifacts verify active-player calibration. The Phase 12 spec may describe candidate bridge approaches, but implementation should wait unless David explicitly expands scope after reviewing the artifacts.

## 6. Position-Specific Research

### QB

QB passed prior promotion work and is structurally critical in Superflex. Phase 12 should not modify QB features. It should report:

- fold-level rank correlation;
- calibration by predicted decile;
- top-disagreement market cases;
- uncertainty intervals.

Potential future work: rushing contribution and age-curve/rushing-floor decay, but only after backtest gating.

### RB

RB feature expansion is tempting but should not be Phase 12 core. The best candidate future features are:

- weighted opportunity;
- targets per game;
- route participation;
- high-value touches;
- red-zone touches;
- yards before contact/contact context;
- possibly expected fantasy points as a denoised opportunity benchmark.

Weighted opportunity and high-value touches are the strongest research-backed candidates, but claims like "0.95+ correlation" must be validated locally before becoming model inputs. RYOE should be treated cautiously. The research reports flag weak year-over-year stability. It may be useful as context or a risk/upside note, but not as a promoted predictive feature without a gate.

Phase 12 should instead publish the RB model's current calibration and subgroup weaknesses, making the later feature-expansion test measurable. RB age research can be reported descriptively as a peak-window diagnostic, but the constitution's locked rule remains: no hardcoded predictive age cliff; the age-26 warning is display context only.

### WR

WR appears comparatively stable. Phase 12 should focus on reporting, not feature churn:

- YPRR and target-earning context in model cards;
- residual diagnostics by age and target share;
- market-disagreement examples;
- calibration reliability by decile.

Future WR work can test target-share growth and route participation, but this is not urgent if current gates hold.

### TE

TE remains the highest-priority model-diagnosis problem after Phase 12.

Why TE is hard:

- role heterogeneity: inline blocker, move TE, big slot, receiving specialist;
- small effective sample sizes;
- touchdown-driven fantasy variance;
- slower development curves;
- NFL draft capital can select real-football blockers who lack fantasy utility;
- public alignment data may not provide clean per-player inline/slot/wide rates at scale.

Best free/probable proxies for a future TE remodel:

- route participation;
- routes per team dropback;
- targets per route run;
- yards per route run;
- snap share;
- aDOT;
- YAC per reception;
- team 12/13 personnel usage;
- formation/personnel proxies from nflverse participation data.

Useful implementation leads for the later TE phase:

- `nflverse` / `nflreadpy` participation data may expose route and personnel context.
- Public 2023+ participation data has FTN lineage and may update on a delayed cadence, so it should not be assumed available for live in-season scoring.
- True player-level alignment is likely limited without paid charting; formation/personnel proxies can stage hypotheses but should not be treated as ground truth.
- Archetype clustering may be worth testing later to separate receiving specialists from blocking-heavy TEs.

Phase 12 should diagnose TE failure but not remodel TE. The model card should state whether TE fails because of rank, calibration, market comparison, sample size, or role-feature absence.

## 7. Trust Surface v2 Requirements

The Trust Surface should become the readable front door to backtest evidence.

### What It Should Show

Per position:

- model version, run ID, git SHA, run date;
- training/fold windows;
- feature list and prohibited-feature check;
- promotion grade and gates;
- RMSE/MAE, Kendall tau-b, Spearman rho;
- calibration decile table;
- NDCG model-vs-market;
- market source/snapshot dates;
- known limitations;
- "experimental" or "validated" status;
- links/paths to raw artifacts.

Model card sections should follow the Mitchell et al. pattern closely enough to be repeatable:

1. **Model details**: engine version, run ID, git SHA, training window, feature list, Ridge alpha.
2. **Intended use**: Dynasty trade, roster, rookie, and hold/sell decision support for David's Superflex PPR league.
3. **Factors**: position, age, sample size, draft capital where applicable, role/usage coverage.
4. **Metrics**: RMSE, MAE, Kendall tau-b, Spearman rho, calibration data, NDCG@12/@24.
5. **Evaluation data**: fold definitions, holdout years, sample sizes, market snapshot dates.
6. **Training data**: source files, feature vintage, labels, exclusions, known missingness.
7. **Quantitative analyses**: subgroup performance by age, draft capital, projection tier, and role proxy.
8. **Ethical/product caveats**: decision aid only, market-overlay separation, no TE decision-grade claims.
9. **Caveats and recommendations**: limitations, prohibited uses, counter-argument requirements, next validation step.

For individual player use later:

- predicted PPG;
- percentile/rank context;
- confidence interval or uncertainty bucket;
- key model drivers if available;
- market overlay divergence;
- caveats;
- counter-argument / red-team case for strong recommendations.

### What It Must Not Imply

- TE is decision-grade.
- DVS is trustworthy before calibration and bridge validation.
- Market data is ground truth.
- A model disagreement with market is alpha before G4 evidence.
- A hard age cliff is a model input.

## 8. Recommended Phase 12 Scope

### In Scope

1. **Operational backtest run**
   - Run `scripts/run_backtest.py --all`.
   - Optionally run TE separately if `--all` remains active positions only.
   - Persist artifacts under `app/data/backtest/runs/`.

2. **Artifact schema expansion**
   - Add or formalize schemas for prediction ledgers, calibration reports, market-comparison ledgers, gate summaries, and model cards.

3. **Model cards**
   - Generate one card per position.
   - Use sections aligned to model-card best practice: intended use, model details, training/evaluation data, metrics, caveats, limitations, recommendations.

4. **Trust Surface v2**
   - Extend the route to serve model cards and artifact summaries.
   - Keep API read-only. No recomputation.
   - Return clear missing-artifact and stale-artifact states.

5. **Divergence ledger v0**
   - Persist passive model-vs-market disagreement rows.
   - Do not promote divergence as predictive alpha yet.

6. **DVS guardrail**
   - Keep `dynasty_value_score` null or explicitly provisional.
   - If a percentile-only v0 is exposed, label it as within-position only and not trade currency.
   - Document candidate DVS calibration math in an appendix, including VORP anchoring, isotonic calibration, uncertainty bands, and why a 0-10,000 trade scale is deferred.

7. **Documentation**
   - Add `ARTIFACTS.md` or equivalent documentation describing artifact locations, fields, and interpretation.

### Out of Scope

- New RB features.
- TE model retraining.
- Cross-position DVS production score.
- Engine A/Engine B blended valuation.
- Market data as model inputs.
- Deployed calibration transforms.
- Frontend polish beyond exposing trust evidence.

### Acceptance Criteria

- Operational artifacts exist for QB/RB/WR and an explicit TE experimental artifact.
- Trust Surface returns artifact summaries without recomputing.
- Every active position has a model card.
- TE model card explains experimental status with quantitative evidence.
- Calibration data is persisted per position.
- Market-comparison metrics are persisted or explicitly marked unavailable/deferred.
- Code review confirms market data never enters features, labels, imputation, scaling, or model fitting.
- DVS status is explicit: null, provisional within-position percentile, or deferred by spec decision.
- Model cards include a counter-argument / limitation section for any position labeled decision-grade.
- Tests cover missing artifacts, stale artifacts, schema validation, and read-only route behavior.

### Test Strategy

- Unit tests for artifact serializers and schema validation.
- Unit tests for calibration/report transforms.
- Contract tests for Trust Surface v2 response shape.
- Integration test for CLI artifact generation in a temp output directory.
- Golden tests for known gate-summary fields.
- Regression tests that scan feature columns for market-derived leakage.

## 9. Data Dependencies

No new source should be required for Phase 12 core.

Existing dependencies:

- Engine B feature CSV.
- Phase 10/11 backtest harness.
- Market snapshot store.
- FantasyCalc/KTC/DP archive data where already ingested.
- nflverse/nflreadpy only as already used by the existing pipeline.

Future feature phases may use:

- nflreadpy/nflverse participation data;
- PFR advanced receiving/rushing stats;
- Next Gen Stats rushing/receiving;
- ffopportunity expected fantasy points;
- FTN charting subset where licensing permits.

Those are **not** Phase 12 core dependencies.

Research note: `nflreadpy` should remain the preferred Python ingestion direction for future nflverse work. Participation data is especially relevant for TE and RB follow-on phases, but public availability and refresh cadence need to be verified before any spec treats it as operational.

### Future nflverse Reference

These endpoints are planning references for later feature phases, not new Phase 12 core dependencies:

| Endpoint | Use | Relevance |
|---|---|---|
| `load_pbp` / `import_pbp_data` | Play-by-play, EPA/WPA | Feature engineering base and QB context |
| `load_player_stats` / `import_weekly_data` | Weekly box-score stats | Realized PPG labels and fold outputs |
| `load_nextgen_stats` / `import_ngs_data` | NGS passing/rushing/receiving | CPOE, aDOT, RYOE context |
| `load_participation` | Personnel, formation, defenders | TE formation/personnel proxies |
| `load_ftn_charting` | Charting subset, 2022+ | Future TE/RB context; limited history |
| `load_pfr_advstats` | Routes, YPRR components, broken tackles | Route participation and efficiency context |
| `load_snap_counts` | Weekly snap counts | Role share and availability context |
| `load_ff_opportunity` | Expected fantasy points | Future denoised opportunity benchmark |

## 10. Open Questions for David

1. Should Phase 12 include a 2024 fold extension if 2025 outcome data is considered settled, or should the first artifact run stay strictly within the Phase 10/11 fold definitions?
2. Should TE be included in `run_backtest.py --all`, or should TE remain opt-in to avoid accidental operational use?
3. Should `dynasty_value_score` remain null, or should Phase 12 expose a clearly labeled within-position percentile v0?
4. Should the Trust Surface be owner-only language, or written as if it might be shared externally?
5. Should the divergence ledger be passive storage only, or should Phase 12 include a simple report of the largest model-vs-market disagreements?
6. Is a future DVS target scale preferred: 0-100, 0-10,000, or rank + percentile with no cardinal score yet?
7. Should future pick valuation be included in the DVS design appendix, or held for a dedicated Trade Lab phase?

## 11. Source Appendix

Sources listed below are inherited from the two input reports. The merged recommendation weights sources by governance fit and avoids treating market sources as truth.

- KeepTradeCut site and FAQ: crowdsourced keep/trade/cut market sentiment, 0-9999 style value scale, separate Superflex/1QB context.
- FantasyCalc site and research pages: trade-derived value estimates, frequent market updates, volatility concepts.
- DynastyProcess documentation and GitHub data: transparent ECR/value-curve methodology, rookie pick value modeling, Superflex conversion concepts.
- Mitchell et al., "Model Cards for Model Reporting" (2018): model-card structure used to frame Trust Surface v2.
- nflverse/nflreadr/nflreadpy documentation: participation, FTN charting, Next Gen Stats, PFR advanced stats, snap counts.
- ffopportunity documentation: expected fantasy points / opportunity modeling candidate for later phases.
- 4for4, ESPN, Apex, FantasyLife, PFF, Sharp Football, nfelo, Footballguys, BrainyBallers: position aging curves, TE development, RB opportunity and RYOE stability, route/target efficiency context.
- Phase 10/11 Backtest Harness Research and Dynasty Genius governance docs: local source of truth for market-overlay isolation, promotion gates, and Trust Surface expectations.

## 12. Bottom Line

The two reports agree on the long-term destination: Dynasty Genius needs a trustworthy valuation layer that can explain itself. They disagree on the immediate next move.

The correct Phase 12 is not the unified score yet. The correct Phase 12 is the evidence layer that makes the unified score safe to build.

Phase 12 should generate operational backtest artifacts, expose them through Trust Surface v2, diagnose TE, and define the DVS guardrails. DVS normalization, TE remodeling, and RB feature expansion should come after those artifacts establish the baseline.
