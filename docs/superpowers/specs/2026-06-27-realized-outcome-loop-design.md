# Realized-Outcome Loop v1 — "Outcome Forward-Accrual" (Design Spec)

**Date:** 2026-06-27
**Status:** DRAFT v2 — Codex round-1 defects (D1–D5) integrated; Gemini no concerns. Pending Codex round-2 re-CLEAR and David commit authorization.
**Author:** Claude (implementation), with cockpit input (Codex technical, Gemini product-edge).
**Phase:** War Room roadmap item #3 (Trust Console track record), backend foundation.
**Governs / governed by:** `00-product-constitution.md` → *In-Season Estimate Responsiveness And Model-Change Governance* (David-ratified 2026-06-27); the compounding-product lens (`02-agent-operating-loop.md`); market-overlay separation; `decision_supported=False` discipline.

---

## 1. Purpose

Continuously score the **frozen model's** predictions against actual NFL fantasy production as it materializes, to build a compounding, descriptive track record of how well the model forecasts — leading with **rank accuracy** and **model-input fidelity**, not noisy box-score points.

This is the backend foundation of David's standing #2 priority: once the season starts, the product must test the model against reality every day, look for what is working and what is not, and improve the model deliberately over time. This loop produces the *measurement* half of that mandate. Per the ruling, it never auto-changes the model; it measures the frozen model and surfaces findings for human-gated improvement.

We score the **frozen model artifact's** projection (the anchor), NOT the daily estimate overlay.

## 2. The horizon constraint (shapes the whole design)

Engine B predicts `avg_ppg_t1_t2` — the mean PPG over the **next two seasons** (Superflex Full PPR, via nflreadpy `fantasy_points_ppr`). Live model-output PIT capture began **2026-06-24**, and it is the off-season.

Consequences:
- No live outcomes until ~Sept 2026.
- No fully **settled** 2-year grade until ~early 2028.
- Therefore v1 is **forward-accrual**: an *interim tracking* state in-season (partial, descriptive) plus *settled grades* later when horizons mature. A settled-only scorer would deliver nothing until 2028.

## 3. Scope

### In scope (v1, backend only)
1. Companion prediction-snapshot table extending the existing model PIT capture (raw `projection_2y` + prediction-time utilization snapshot).
2. Point-in-time identity bridge (sleeper ↔ gsis ↔ dg ↔ pfr).
3. Weekly in-season realized-outcome ingestion store (survivorship-complete).
4. Pure scorer producing per-player tracking rows + aggregate cohort metrics.
5. Descriptive scorecard artifact + CLI producer (+ optional weekly LaunchAgent).

### Out of scope (later increments)
- Any API route or UI surface (frontend HOLD intact; a read-only API + UI are separate scoped increments).
- Off-season historical "retrospective baseline" (would require true historical model vintages we do not have — `MODEL_PIT_INADEQUATE`; the legitimate source is the existing walk-forward backtest, deferred).
- Gemini's "audit the league" angle (score the edge vs league-mates' rosters).
- Model-vs-market scorekeeping (Gate-4-adjacent; the model overlay/market wall holds).
- Automated settled-grade promotion or any model retrain/adjustment (human-gated by ruling).

## 4. Architecture

Three physically separate stores plus one derived artifact (Codex Q1 — never co-mingle predictions, outcomes, and derived joins):

```
model_forward_capture.db            frozen predictions (EXISTING — core schema UNTOUCHED)
  └─ prediction_snapshot (NEW companion table, same PK)
                                    projection_2y + prediction-time utilization snapshot
outcome_forward_capture.db (NEW)    realized weekly / season-to-date production + utilization
realized_outcome_scorecard.* (NEW)  derived per-player tracking rows + cohort metrics (artifact)
```

### 4.1 Companion prediction-snapshot table (NEW)
- **Why a companion table, not new columns on the core store:** the core store's immutability/vintage signature is `_CONTENT_COLUMNS`. Adding columns to it would change that signature and cause re-capture conflicts. A companion table keyed to the **same** primary key `(capture_date, source, semantic_output_hash, provenance_hash, player_key)` preserves the existing semantic-hash/vintage contract entirely (Codex Q3 + D2).
- **Fields:** the PK columns; `projection_2y` (raw predicted PPG from the PVO row); a utilization snapshot drawn from the **canonical resolved-feature-source columns** — `snap_share`, `route_participation`, `target_share_nfl`, `air_yards_share`, `weighted_opportunity`, `yprr`, `tprr` — each stored with a `role` tag (`model_input` | `diagnostic_only`) because some of these are Engine B model inputs only for certain positions and others are diagnostic/excluded from the model matrix (Codex D2); `prediction_ppg_status` (`captured` | `missing_legacy_capture` | `capture_incomplete`); `util_snapshot_status`; `schema_version`; `source_hash`. Only fields actually present in the resolved feature source for that capture are recorded (others null with status), never assumed.
- **Atomicity / rollout-status (Codex D1):** the core PIT row and its companion row are written in **one transaction**. If that is not possible, a post-rollout core row missing its companion is `prediction_ppg_status=capture_incomplete` and fails closed (excluded from scoring with a count) — it is **never** silently treated as legacy. A `schema_version` / rollout marker makes "legacy, captured before the companion table existed" distinguishable from "post-rollout companion write failed."
- **Legacy rows** (captured before this table existed) are `prediction_ppg_status=missing_legacy_capture` with null projection/util — never retroactively mutated unless artifact bytes are available and hash-matched (Codex D2).
- **Write path:** populated by the existing daily 09:30 model-PVO-refresh capture driver, extended to also write the companion row when it captures a model PIT row. Must be isolated from any active dashboard route so first writes cannot 503 (Gemini).

### 4.2 Point-in-time identity bridge (NEW)
- Predictions are sleeper-keyed; outcomes are gsis-keyed. A dedicated bridge resolves them — never an ad-hoc join in the scorer (Codex Q5/D).
- **Fields:** `sleeper_id`, `dg_player_id`, `gsis_id`, `pfr_id`, `season`, `valid_from`/`valid_to` (or `snapshot_date`), `source_hash`, `resolution_status`.
- **Point-in-time rule:** resolve a prediction to an outcome using the mapping valid **at the prediction's capture date**, not today's mapping.
- **Fail-closed:** unresolved identity → excluded from scoring with an explicit count in the report; many-to-one conflict → abort or quarantine (never silently pick one).

### 4.3 Outcome ingestion store (NEW, `outcome_forward_capture.db`)
- **Weekly in-season** pull of nflreadpy player_stats → realized `fantasy_points_ppr` → per-player season-to-date PPG, rolling 3/5/8-game windows, games played, and realized utilization (snap/route/target).
- **Append-only, survivorship-complete:** retired/injured/cut/benched players are retained with explicit status, never silently dropped.
- Mirrors the existing capture stores' immutability + semantic-hash pattern.
- **Week-finalized gate (Codex Q4):** only ingest/score a week once **all** of that week's games are final; if any game is missing/postponed/unknown → `week_status=not_finalized` and no-op (do not score a half-finalized week).

### 4.4 Scorer (NEW, pure)
Joins captured predictions (via the companion snapshot + identity bridge) to realized outcomes and emits:

- **Per-player tracking rows:** `predicted_ppg` (`projection_2y`), realized-to-date PPG, `realized_vs_expected_delta`, `maturity_pct`, `settlement_status` (`partial` | `settled`), and the Model-Input-Fidelity deltas (§5.2).
- **Aggregate cohort metrics:** within-position rank metrics (Spearman / NDCG / Precision@k) via the existing `backtest_metrics.py`, plus a Model-Input-Fidelity summary.
- Everything `decision_supported=False`, with maturity/power-floor caveats.

### 4.5 Report producer + CLI (+ optional weekly LaunchAgent)
- A **read producer** emitting the descriptive scorecard artifact (per-player tracking + cohort aggregates). No store mutation beyond writing the gitignored artifact.
- **Cadence:** weekly in-season, after the week's stats finalize (mirrors the existing 09:xx daily-job + LaunchAgent pattern; exact trigger time TBD in the plan). **Off-season = honest no-op exit.**
- `--preflight` readiness-only mode; honest exit codes; never auto-commits.

## 5. Metric definitions

### 5.1 Rank accuracy (headline #1)
Within-position rank quality comparing the model's predicted ordering to realized ordering. **CI coverage is metric-specific (Codex D3) — the spec does not claim uniform BCa CIs:**
- **Spearman ρ / Kendall τ:** via `backtest_metrics.compute_rank_correlation()` — BCa CIs available.
- **NDCG:** via `compute_ndcg()` — **point estimate only** in v1 (the existing BCa path `compute_ndcg_diff_bootstrap()` is a model-vs-market comparison, which v1 defers). A model-only NDCG bootstrap is out of v1 scope.
- **Precision@k:** define the top-k realized "truth" set explicitly and report point estimate / counts; no generic model-only BCa CI in v1.

**Status gating, no maturity-weighting in v1 (Codex D4/D5):** rank metrics are **status-gated**, not weighted by a hand-tuned maturity formula. A position cohort's rank metrics are not surfaced until it clears explicit floors: **≥ 4 eligible observed games per player** and **≥ a minimum cohort size per position** (exact per-position minimums fixed in the implementation plan against real cohort counts). Below the floor, the metric is emitted with `status=power_floor_not_met` and is descriptive-only — never shown as a settled-looking number. No maturity-weighted rank metric in v1.

### 5.2 Model Input Fidelity / Utilization Deviation (headline #2)
**Renamed from "utilization-alignment" (Gemini)** to frame it unambiguously as a *technical audit of the model's inputs*, not a score of the player's outlook. It answers: *does the usage that justified this projection still hold?*
- Computed as plain deltas (Mean Absolute Deviation / signed delta) between the **prediction-time utilization snapshot** (the `role=model_input` fields from §4.1) and the **realized 4-week rolling utilization** (4 weeks — 1–2 weeks is too volatile to game-script noise; Gemini Q2).
- **Early-season gating (Codex D4):** no 4-week delta is emitted before **≥ 4 observed eligible games/weeks** exist. Below that, the field carries `status=partial_window` and no deviation value — never a delta computed against a stub window.
- Reported as descriptive per-field deltas, e.g. `route_participation_delta: -5.2%`. Never combined into a single "fidelity score" that could read as a player verdict.

### 5.3 Raw PPG residual / calibration (secondary)
`realized_vs_expected_delta` on raw PPG is captured and shown as **maturing/secondary**; a true calibration grade is **settled only at horizon completion** (T+2 done). In-season it is explicitly partial.

## 6. Survivorship handling (both agents, emphatic)
Keep **every** captured player in the rank cohort. A player who plays 0 games (injured/cut/retired) is assigned a floor value:
- **Settled grades (LOCKED):** a player with 0 settled-horizon games is assigned the **position 5th-percentile cohort penalty (Gate-4 parity)** — not 0.0 PPG. This matches the existing Gate-4 survivorship design and avoids an artificially harsh 0.0 distorting rank metrics (Codex §12 / Gemini).
- **Weekly tracking:** distinguish bye / injury / not-yet-played from a true departure; do not penalize a bye as a miss, but do not silently drop a genuine departure. Removing failed picks from the cohort would manufacture survivorship bias and make the model look better than it is.

## 7. Honesty & governance guards
- `decision_supported=False` recursive across every emitted row and the scorecard root.
- Score the **frozen model** (the anchor), never the daily estimate overlay; consistent with the new ruling.
- Market data stays an overlay, excluded from scoring inputs (model-vs-market scorekeeping is a deferred increment).
- Banned-language discipline: descriptive identifiers only (`realized_vs_expected_delta`, `route_participation_delta`), never buy/sell/target/tier/verdict.
- Non-dismissible power-floor / maturity caveats in early weeks.
- Off-season no-op preserves data hygiene (no look-ahead backfill).
- Schema additions isolated from active dashboard routing (no 503 on first writes).

## 8. Robustness boundary (per operating-loop §8)
- **API-misuse (wrong argument types) → fail loud.**
- **Data-corruption (malformed outcome rows, missing fields) → fail closed:** no-op with an explicit report, never guessed/imputed values.
- **Semantic/range/finiteness validation:** non-finite PPG/utilization, negative games, out-of-range deltas → rejected with explicit status, never silently scored.

## 9. Error handling summary
- Missing/malformed outcome data → fail-closed no-op + report.
- Unresolved identity → excluded with explicit count.
- Many-to-one identity → quarantine/abort.
- Legacy captures → `missing_legacy_capture`.
- Week not finalized → no-op.
- Off-season → honest no-op exit.

## 10. Testing strategy
- **Pure scorer unit tests:** rank metrics, status/power-floor gating (`power_floor_not_met`), Model-Input-Fidelity deltas + `partial_window` gating, settled-vs-partial boundary, metric-specific CI coverage (Spearman BCa vs NDCG point-estimate).
- **Identity-bridge tests:** point-in-time resolution, unresolved exclusion with count, many-to-one quarantine.
- **Survivorship tests:** 0-game floor, bye vs injury vs departure distinction, no silent drops.
- **Falsification matrix** (RED author seeds; reviewers challenge): valid-nominal, boundary, missing, null/None, wrong-type, malformed-shape, duplicate/conflict, empty-collection, cross-component-shape, non-finite/NaN/inf, synthetic/override.
- **Idempotency:** same-week re-runs produce no duplicate appends.
- **Off-season no-op** and **week-not-finalized no-op** tests.
- Companion-table tests proving the **core store's immutability/vintage signature is unchanged**.

## 11. Build sequence (proposed; finalized in the implementation plan)
1. Companion prediction-snapshot table + capture-driver write extension (projection_2y + util snapshot; immutability preserved).
2. Point-in-time identity bridge.
3. Outcome ingestion store + week-finalized gate.
4. Pure scorer (rank metrics, Model Input Fidelity, residual, survivorship, maturity/power floors).
5. Scorecard report producer + CLI (+ optional weekly LaunchAgent).

Each task: cockpit-TDD (Codex RED → Claude GREEN → dual-CLEAR → David-authorized commit → both-lane post-commit zero-divergence), per the operating loop.

## 12. Resolved decisions and remaining plan-time items

**Resolved in-spec (Codex round-1 D5 — no longer open):**
- **Placement LOCKED:** `projection_2y` and the utilization snapshot live in the companion table (§4.1), never the core store.
- **Settled 0-game floor LOCKED:** position 5th-percentile penalty (Gate-4 parity), not 0.0 (§6).
- **No maturity-weighted rank metric in v1:** status gating only (§5.1).
- **Power floors set:** ≥ 4 eligible games per player; per-position minimum cohort size (numeric minimums calibrated to real cohort counts in the plan); below-floor → `power_floor_not_met`, descriptive-only (§5.1).
- **Early-season MIF gating:** no 4-week delta before ≥ 4 eligible games; `partial_window` otherwise (§5.2).
- **Week-finalized gate logic:** defined in §4.3 (all of a week's games final, else `not_finalized` no-op).

**Genuinely plan-time / operational (not spec-blocking):**
- The exact LaunchAgent trigger time and the concrete nflreadpy call used to confirm all of a week's games are final.
- The exact numeric per-position minimum cohort sizes (calibrated against real 2026 cohort counts during the build).

## 13. Cockpit input incorporated
- **Codex:** three separate stores; companion table to preserve immutability; util snapshot limited to available feature columns; legacy `missing_legacy_capture`; survivorship distinctions; power floors on partial rank metrics; week-finalized gate; identity bridge fail-closed.
- **Gemini:** rename to Model Input Fidelity / Utilization Deviation (audit of inputs, not player score); 4-week rolling window; deltas as MAD/signed; keep all players in cohort with floor for 0-games; off-season no-op correct; banned-language + dashboard-routing isolation checks.
