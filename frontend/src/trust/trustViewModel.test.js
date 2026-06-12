import { describe, expect, it } from "vitest";

const gate = {
  g1_rank_correlation_pass: true,
  g2_rmse_stability_pass: false,
  g3_market_superiority_pass: "deferred",
  g4_divergence_validity_pass: "insufficient_data",
  overall_grade: "EXPERIMENTAL",
  promotion_justification: "Confidence intervals include zero.",
};

const fold = {
  fold_index: 1,
  train_years: [2018, 2019],
  test_year: 2020,
  outcome_seasons: [2021, 2022],
  n_train: 120,
  n_test: 34,
  kendall_tau: 0.18,
  kendall_tau_bca_ci95: [-0.03, 0.31],
  spearman_rho: 0.24,
  spearman_rho_bca_ci95: [-0.01, 0.42],
  rank_ic: 0.24,
  rmse: 3.8,
  mae: 2.9,
};

function trustSurfaceFixture() {
  return {
    experimental: true,
    folds: [fold],
    git_sha: "abc1234",
    market_snapshot_dates: { 2020: "2026-05-31" },
    market_source: "dp_archive",
    market_source_label: "dynastyprocess_ecr_2qb",
    model_artifact_hash: "hash-qb",
    model_card_available: true,
    model_reliability: {
      caveat: "QB magnitude predictions carry elevated uncertainty.",
      position: "QB",
      r2_oos_mean: 0.14,
      spearman_rho_mean: 0.31,
    },
    model_version: "engine_b_v2",
    overall_grade: "EXPERIMENTAL",
    position: "QB",
    promotion_gate: gate,
    retrain_mode: "refit_per_fold_fixed_alpha",
    ridge_alpha: 500,
    rmse_stability: {
      rmse_cv: 0.08,
      rmse_max_deviation_pct: 0.15,
      rmse_mean: 3.8,
      rmse_per_fold: [3.8],
    },
    run_date: "2026-05-31T00:00:00Z",
    run_id: "483f87f9-1a16-4750-a825-0165c7335696",
    schema_version: "1.0.0",
  };
}

function modelCardFixture() {
  return {
    backtest_run_id: "483f87f9-1a16-4750-a825-0165c7335696",
    caveats: ["Decision support disabled."],
    generated_at: "2026-06-10T00:00:00Z",
    intended_use: "Read-only trust review.",
    is_experimental: true,
    known_failure_modes: ["Small cohorts can be unstable."],
    out_of_scope_uses: ["Roster-action recommendations"],
    position: "QB",
  };
}

describe("buildTrustConsoleViewModel", () => {
  it("maps validated API responses into the curated trust console view model", async () => {
    const { buildTrustConsoleViewModel } = await import("./trustViewModel");
    const viewModel = buildTrustConsoleViewModel(
      trustSurfaceFixture(),
      modelCardFixture(),
    );

    expect(viewModel.position).toBe("QB");
    expect(viewModel.overall_grade).toBe("EXPERIMENTAL");
    expect(viewModel.experimental).toBe(true);
    expect(viewModel.gates).toEqual(gate);
    expect(viewModel.folds).toEqual([fold]);
    expect(viewModel.model_reliability?.caveat).toContain("elevated uncertainty");
    expect(viewModel.market).toEqual({
      source: "dp_archive",
      label: "dynastyprocess_ecr_2qb",
      snapshot_dates: { 2020: "2026-05-31" },
    });
    expect(viewModel.provenance).toEqual({
      run_id: "483f87f9-1a16-4750-a825-0165c7335696",
      run_date: "2026-05-31T00:00:00Z",
      model_version: "engine_b_v2",
      model_artifact_hash: "hash-qb",
      git_sha: "abc1234",
    });
    expect(viewModel.model_card?.intended_use).toBe("Read-only trust review.");
  });

  it("does not expose raw BacktestResult-only or model-card provenance fields", async () => {
    const { buildTrustConsoleViewModel } = await import("./trustViewModel");
    const viewModel = buildTrustConsoleViewModel(
      trustSurfaceFixture(),
      modelCardFixture(),
    );

    expect(viewModel).not.toHaveProperty("ridge_alpha");
    expect(viewModel).not.toHaveProperty("retrain_mode");
    expect(viewModel).not.toHaveProperty("rmse_stability");
    expect(viewModel).not.toHaveProperty("schema_version");
    expect(viewModel.model_card).not.toHaveProperty("model_version");
    expect(viewModel.model_card).not.toHaveProperty("model_artifact_hash");
    expect(viewModel.model_card).not.toHaveProperty("git_sha");
  });
});
