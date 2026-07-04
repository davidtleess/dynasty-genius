# Rookie-Filter Prior Recalibration — v2 Unconditioned Band×Horizon Table

**Date:** 2026-07-04 · **Author:** Claude (implementation lead) · **Status:** DRAFT v2 — Codex R1 ×7 integrated (with Claude countering #2: outcome is role-row-direct at entry+H, not a label join — the label anchor would reintroduce the conditioning); Gemini fork-resolution ACCEPTED; cockpit dual-CLEAR (Codex counter-ACCEPTED role-row-direct + CLEAR; Gemini fork-accepted); pending David gate
**Trace:** BUILD-4 T5 named ticket (the conditioned table exposed the v1 priors as population-mismatched); David board item 1, 2026-07-04.

## 0. The problem and the honest fix

The T4 rookie filter carries registered v1 headline priors (`capital_qualified` 0.63 / `day3` 0.15 / `undrafted` 0.05). The T5 record's conditioned table (round-1 *who-played* survival 0.911/0.804/0.750) measures a DIFFERENT population — QBs with a games≥4 feature row. The filter runs at draft time on the UNCONDITIONED class; copying conditioned numbers in would be the survivorship error the T5 record itself warns about. **The fix: compute TRUE unconditioned survival from our own sources — cohort = ALL rookie QB entrants in rosters with `entry_year` 2018–2023 (numeric `draft_number` banded; missing/NA = undrafted — the cohort includes UDFAs by construction, Codex R1 #1); outcome@H = the role-occupancy predicate (games ≥ 8 AND snap_share ≥ 0.50) evaluated DIRECTLY at season `entry_year`+H from the T1 role rows (`aggregate_qb_role_source`), absent role row → negative — NEVER a label-table join, because the label table is feature-row-anchored and inherits the games≥4 conditioning this build exists to remove (Claude R1 counter to Codex #2: an entry-year-label join would count a sit-then-start Jordan Love all-negative, contradicting the disclosed H1-negative/H2-positive semantics). Negatives count ONLY in horizons whose outcome window is structurally observable.**

Gemini's falsifiable pre-registered predictions (recorded BEFORE computation; the run tests them): R1 H1 0.80–0.88 · R2 H1 0.45–0.50 · day3 H2 0.05–0.08 · UDFA 0.01–0.02.

## 1. Scope (Codex counter-scope adopted; the classification fork resolved)

- **A dedicated producer** (`scripts/compute_rookie_qb_unconditioned_priors.py`, frame-injectable per house pattern) emitting the **registered v2 prior table**: rows keyed `capital_band` (`round_1_picks_1_32` / `round_2_picks_33_64` / `day3_picks_65_plus` / `undrafted`) × `horizon` (1/2/3) with `n`, `positives`, `rate`, `basis`, plus generation metadata per the T5 evidence pattern. Committed as a tracked artifact (`app/config/rookie_qb_prior_table_v2.json`) — priors are registered constants-with-provenance, not folklore.
- **Filter integration (H1-compatible):** `qb_rookie_risk_filter.py` keeps its EXACT public classification contract (`capital_qualified`/`day3_insufficient_capital`/`undrafted_insufficient_capital` — binary capital line unchanged) and keeps returning `base_rate_survival_prior` as the H1 headline — now sourced from the v2 table by the row's **finer `capital_band`, which is added as a disclosed output column** alongside the per-horizon table reference. **Fork resolution (Claude position, both lanes' substance preserved):** Gemini's regime-chasm demand is satisfied in the NUMBERS (a round-2 QB gets the round-2 prior, visibly banded); Codex's contract-stability ruling holds (splitting the public classification strings = downstream churn = a named separate David-gated item).
- Prohibited unchanged: exact-set input wall, no NFL-usage columns, `engine_b_training_integration=False`, `decision_supported=false` everywhere.

## 2. Computation contract (Codex mechanics)

- **Cohort:** all rookie QB entrants in rosters, `entry_year` 2018–2023, including missing/NA `draft_number` as undrafted. Identity/crosswalk failures → **quarantined + disclosed, never counted as negatives**. **Roster repetition semantics (Codex R1 #3):** rosters repeat per season — identical repeated rows per `player_id` collapse; CONFLICTING `entry_year`/`draft_number` values fail closed (normal multi-season repeats are not conflicts).
- **Outcome evaluation (role-row-direct, per §0):** for each cohort member and horizon H, evaluate the role predicate at season `entry_year`+H from the role rows: role row present → games≥8 AND snap_share≥0.50 (snap-missing → games-only fallback, basis counted); role row absent → negative. Observability computed from the max available role/source season — never a hardcoded year (a 2023 draftee's H3 needs 2026 outcomes → excluded from the H3 denominator, not counted).
- **Denominator honesty:** structural exclusions are not denominator rows; per-band×horizon `n`/`positives` disclosed so every rate is checkable.
- Zero-snap honesty (Gemini seed 2): a drafted QB with no NFL appearance at all is an H-negative in observable horizons — the survivorship correction this build exists for.

### Artifact schema pins (Codex R1 #4)
`app/config/rookie_qb_prior_table_v2.json` is runtime policy (the registry precedent), never opaque generated data: required metadata = `config_version`, `generated_at`, `generation_command`, `machinery_repo_sha`, `source_caveat`, `cohort_entry_years`, `max_available_role_season`, `decision_supported: false`; **no auto-regeneration side effect** (the producer writes only when invoked; the filter only reads). Rates stored NUMERIC with checkable `n`/`positives` (whole-percent rounding is DISPLAY-only, Codex R1 #5). **Zero-denominator rule (Codex R1 #6):** every runtime-consumed H1 band row requires `n > 0`; non-H1 structurally-observable empty cells are `rate: null` (never 0.0), and the filter refuses a null it would consume.

## 3. Surfacing honesty (Gemini part 3 — binding on any future display, recorded now)

Wherever these priors render David-facing (the filter output today; any Rookie Board surface later): the complement renders with equal prominence ("historical bust/bench rate" = 1−rate); **displayed rates round to whole percentages** (decimal precision overclaims at these n); small-band volatility disclosed ("low sample — day-3/UDFA priors are highly volatile"); the H1 definition disclosed ("active startable role occupancy in year 1" — a Jordan-Love-shaped sit-then-start is H1-negative, H2/H3-positive, and that is the metric working, not a bug).

## 4. Falsification seeds

1. Band separation: a pick-40 QB receives the round-2 prior, never round-1's (Gemini seed 1); band boundaries 32/33 and 64/65 pinned.
2. Zero-appearance honesty: a drafted-never-played QB counts negative in every observable horizon; absent from unobservable ones.
3. Observability: a 2023 draftee appears in H1/H2 denominators but never H3 (window-derived, not hardcoded); the window derives from max available season.
4. Quarantine vs negative: an unresolvable identity is disclosed-quarantined, not silently negative; counts in diagnostics.
5. Table contract: band×horizon rows complete for observable cells; n/positives/rate consistent (`positives ≤ n`, `rate = positives/n`); duplicate band×horizon fails.
6. Filter wiring: headline `base_rate_survival_prior` equals the v2 table's H1 rate for the row's band **via `math.isclose`/`pytest.approx`, never exact float/string equality (Codex R1 #5)**; the `capital_band` column disclosed; public classifications byte-unchanged; existing T4 suite green.
7. Prediction check (report-only, non-gating): the run's rates vs Gemini's pre-registered ranges — misses are FINDINGS to explain, never numbers to adjust.
8. Fail-closed loaders: absent/malformed/duplicate v2 table → the filter refuses (no silent v1 fallback).
9. Determinism + no market/NFL-usage columns anywhere in the computation inputs.

## 5. Task plan

T1 (Codex RED: producer + table contract + observability/quarantine seeds) → T2 (Claude GREEN: producer + real run + the committed v2 table) → T3 (Codex RED: filter wiring) → T4 (Claude GREEN + full closeout) → dual-CLEAR → David gates ship. Branch: `feature/rookie-prior-recalibration-v2`.
