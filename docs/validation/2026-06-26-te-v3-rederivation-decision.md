# te_v3 Re-Derivation Decision (drop role-risk; stability-justified)

Date: 2026-06-26. Status: **te_v3 RE-DERIVED — 14-feature / alpha=100, ACTIVE_B (G3 deferred).**

> **THIS DOCUMENT SUPERSEDES** `phase13-3-3-te-role-risk-decision.md` and
> `phase13-3-te-promotion-decision.md`, whose findings were **invalidated by the Tyler Conklin
> data contamination discovery** (2026-06-26). Those records' role-risk justification and
> promotion evidence were computed on a contaminated seed and no longer hold on clean data.

## 1. What changed and why
The F-feature-refresh go-live surfaced a training-data contamination in the Engine B TE seed:
a seasonless `gsis<->pfr` crosswalk fan-out made one player (Tyler Conklin) 35.3% of the TE
training rows (T1 crosswalk fix + T2 deduped seed). A pre-registered, read-only feature-validity
review (decision-gated) then found:

- **`te_role_is_risk_profile` is null on clean data** — re-running the original Phase-13.3
  bake-off on the deduped seed: 2/4 RMSE-win folds, `passes_acceptance=False` (was 4/4 on the
  contaminated seed). Its "risk-role -> lower value" negative-coefficient signal was largely an
  artifact of the duplicated player inflating the non-risk baseline.
- **No beyond-noise accuracy edge over legacy te_v2** — paired BCa CIs for the ablated 14-feature
  alpha-100 model vs legacy te_v2 all cross zero (RMSE delta -0.031, CI [-0.102, +0.054]).
- **The only categorical justification is G2 stability** — at alpha=1.0 the model FAILS the
  G2 RMSE-stability gate (26.21% > 25%); at alpha=100 it PASSES (10.26%).

Evidence: `docs/validation/2026-06-26-te-role-risk-contamination-finding.md` (finding) +
`docs/validation/2026-06-26-te-v3-rederivation-report.json` (acceptance).

## 2. Decision
- **DROP** `te_role_is_risk_profile` from the Engine B TE model contract (`ENGINE_B_FEATURES_TE`,
  15 -> 14). It remains a computed column (`ENGINE_B_OUTPUT_COLUMNS` / `ENGINE_B_ALLOWED_FEATURES`);
  full pipeline removal is a separate downstream cleanup.
- **RE-DERIVE te_v3** as the 14-feature / alpha=100 model on the deduped seed
  (run `20260626T165649Z`, local-only artifact; manifest updated locally).
- **Promotion grade: ACTIVE_B** — G1 rank PASS, G2 stability PASS (10.26% < 25%), G3 market
  superiority DEFERRED. `model_status=VALIDATED`.

## 3. Honesty (binding)
- **Justified by G2 regularization stability ALONE.** The role-risk feature is abandoned as a
  contamination artifact; the accuracy lift over legacy te_v2 is **within the BCa noise margin**
  and **no accuracy lift is claimed**.
- `decision_supported` remains **False**; no market-derived fields entered model inputs; no
  buy/sell or tier language.

## 4. Boundary / open
- Model + manifest are local-only (gitignored), consistent with existing Engine B handling; only
  the acceptance report + this record are committed.
- **PVO regen deferred** (separate T3b) — live TE valuations refresh only when the PVO is
  regenerated; that is David-gated and out of this build.
- Open follow-ups: gate rmse_max_deviation_pct fraction-vs-percent units cleanup; N:1 snap
  mis-attribution (non-blocking); deployed-model reproducibility (gitignored artifacts).
- Next: the F-feature-refresh sprint (T4 gate semantics -> T5 scheduler Option B -> T6 go-live)
  resumes on this clean re-derived model.
