// @vitest-environment jsdom

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AppShell } from "../shell/AppShell";
import { TrustConsole } from "./TrustConsole";

const TRUST_DIR = join(process.cwd(), "src", "trust");
const TRUST_TRUTH_COPY =
  "Consensus-competitive, edge unproven. Engine B is statistically tied with DynastyProcess ECR expert consensus; per-fold NDCG-diff bootstrap CIs include zero.";

function authoredTrustFiles() {
  if (!existsSync(TRUST_DIR)) {
    return [];
  }
  return readdirSync(TRUST_DIR)
    .filter((name) => /\.(css|jsx?|tsx?)$/.test(name))
    .filter((name) => !name.includes(".test."))
    .map((name) => join(TRUST_DIR, name));
}

const gate = {
  g1_rank_correlation_pass: true,
  g2_rmse_stability_pass: false,
  g3_market_superiority_pass: "deferred",
  g4_divergence_validity_pass: "insufficient_data",
  overall_grade: "EXPERIMENTAL",
  promotion_justification: "Confidence intervals include zero.",
};

function trustSurface(position = "QB") {
  return {
    experimental: true,
    folds: [
      {
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
      },
    ],
    git_sha: "abc1234",
    market_snapshot_dates: { 2020: "2026-05-31" },
    market_source: "dp_archive",
    market_source_label: "dynastyprocess_ecr_2qb",
    model_artifact_hash: `hash-${position.toLowerCase()}`,
    model_card_available: true,
    model_reliability:
      position === "QB"
        ? {
            caveat: "QB magnitude predictions carry elevated uncertainty.",
            position: "QB",
            r2_oos_mean: 0.14,
            spearman_rho_mean: 0.31,
          }
        : null,
    model_version: "engine_b_v2",
    overall_grade: "ACTIVE_B_VALIDATED",
    position,
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

function modelCard(position = "QB") {
  return {
    backtest_run_id: "483f87f9-1a16-4750-a825-0165c7335696",
    caveats: ["Decision support disabled."],
    generated_at: "2026-06-10T00:00:00Z",
    intended_use: "Read-only trust review.",
    is_experimental: true,
    known_failure_modes: ["Small cohorts can be unstable."],
    out_of_scope_uses: ["Roster-action recommendations"],
    position,
  };
}

function okJson(payload) {
  return Promise.resolve({
    ok: true,
    json: () => Promise.resolve(payload),
  });
}

function mockTrustFetch({ cardOk = true, invalidSurface = false } = {}) {
  return vi.fn((input) => {
    const url = String(input);
    const position = url.includes("/RB") ? "RB" : "QB";
    if (url.endsWith("/model-card")) {
      if (!cardOk) {
        return Promise.resolve({ ok: false, json: () => Promise.resolve({}) });
      }
      return okJson(modelCard(position));
    }
    if (invalidSurface) {
      return okJson({ position });
    }
    return okJson(trustSurface(position));
  });
}

describe("TrustConsole", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", mockTrustFetch());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("mounts a minimal Model Trust placeholder with position controls", () => {
    render(<AppShell />);

    fireEvent.click(screen.getByRole("button", { name: "Model Trust" }));

    const main = screen.getByRole("main");
    expect(within(main).getByRole("heading", { name: "Model Trust" })).toBeTruthy();
    for (const position of ["QB", "RB", "WR", "TE"]) {
      expect(within(main).getByRole("button", { name: position })).toBeTruthy();
    }
  });

  it("does not introduce prohibited conclusion wording in authored trust files", () => {
    const trustText = authoredTrustFiles()
      .map((path) => readFileSync(path, "utf8"))
      .join("\n");
    const appShellText = readFileSync(
      join(process.cwd(), "src", "shell", "AppShell.tsx"),
      "utf8",
    );

    expect(`${trustText}\n${appShellText}`).not.toMatch(
      new RegExp("ver" + "dict", "i"),
    );
  });

  it("fetches and validates trust data plus model-card data for the active position", async () => {
    const fetchMock = mockTrustFetch();
    vi.stubGlobal("fetch", fetchMock);

    render(<TrustConsole />);

    expect(screen.getByText("Loading trust data")).toBeTruthy();
    await screen.findByText("Trust data loaded");

    expect(fetchMock).toHaveBeenCalledWith("/api/trust-surface/QB");
    expect(fetchMock).toHaveBeenCalledWith("/api/trust-surface/QB/model-card");
    expect(screen.getByRole("button", { name: "QB" })).toHaveProperty(
      "ariaPressed",
      "true",
    );
  });

  it("refetches both endpoints when the active position changes", async () => {
    const fetchMock = mockTrustFetch();
    vi.stubGlobal("fetch", fetchMock);

    render(<TrustConsole />);
    await screen.findByText("Trust data loaded");

    fireEvent.click(screen.getByRole("button", { name: "RB" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/trust-surface/RB");
      expect(fetchMock).toHaveBeenCalledWith("/api/trust-surface/RB/model-card");
    });
    expect(screen.getByRole("button", { name: "RB" })).toHaveProperty(
      "ariaPressed",
      "true",
    );
  });

  it("degrades the whole shell when trust-surface data is unavailable or invalid", async () => {
    vi.stubGlobal("fetch", mockTrustFetch({ invalidSurface: true }));

    render(<TrustConsole />);

    await screen.findByText("Trust data unavailable");
  });

  it("keeps the trust shell available when only the model card is missing", async () => {
    vi.stubGlobal("fetch", mockTrustFetch({ cardOk: false }));

    render(<TrustConsole />);

    await screen.findByText("Trust data loaded");
    expect(screen.getByText("Model card unavailable")).toBeTruthy();
    expect(screen.queryByText("Trust data unavailable")).toBeNull();
  });

  it("renders the truth panel from the ready-state view model", async () => {
    vi.stubGlobal("fetch", mockTrustFetch());

    render(<TrustConsole />);

    await screen.findByText("Trust data loaded");
    const panel = screen.getByRole("region", { name: "Model trust truth" });
    expect(within(panel).getByText(TRUST_TRUTH_COPY)).toBeTruthy();
    expect(within(panel).getByText("Experimental — not validated")).toBeTruthy();
    expect(within(panel).queryByText("ACTIVE_B_VALIDATED")).toBeNull();
  });

  it("renders the gate matrix from the ready-state view model", async () => {
    vi.stubGlobal("fetch", mockTrustFetch());

    render(<TrustConsole />);

    await screen.findByText("Trust data loaded");
    const matrix = screen.getByRole("region", { name: "Validation gates" });
    expect(within(matrix).getByText("G1 Rank correlation: MET")).toBeTruthy();
    expect(within(matrix).getByText("G2 RMSE stability: UNMET")).toBeTruthy();
    expect(within(matrix).getByText("G3 Market superiority: DEFERRED")).toBeTruthy();
    expect(
      within(matrix).getByText("G4 Divergence validity: INSUFFICIENT DATA"),
    ).toBeTruthy();
  });

  it("renders the fold table from the ready-state view model", async () => {
    vi.stubGlobal("fetch", mockTrustFetch());

    render(<TrustConsole />);

    await screen.findByText("Trust data loaded");
    const table = screen.getByRole("table", { name: "Per-fold backtest results" });
    expect(within(table).getByText("Fold 1")).toBeTruthy();
    expect(within(table).getByText("CI includes zero")).toBeTruthy();
  });
});
