// @vitest-environment jsdom

import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TrustStrip } from "./TrustStrip";

function trustSurfaceResponse(overrides = {}) {
  return {
    divergence_validity: null,
    experimental: true,
    folds: [],
    git_sha: "56b3b84",
    market_snapshot_dates: {
      2025: "2025-09-08",
    },
    market_source: "fc_native",
    market_source_label: "fantasycalc_native",
    model_artifact_hash: "abc123",
    model_card_available: true,
    model_reliability: {
      caveat: "QB magnitude predictions carry elevated uncertainty.",
      position: "QB",
      r2_oos_mean: null,
      spearman_rho_mean: 0.42,
    },
    model_version: "engine_b_v2",
    overall_grade: "EXPERIMENTAL",
    position: "QB",
    promotion_gate: {
      g1_rank_correlation_pass: false,
      g2_rmse_stability_pass: false,
      g3_market_superiority_pass: "deferred",
      g4_divergence_validity_pass: "deferred",
      gate_version: "1.0",
      overall_grade: "EXPERIMENTAL",
      promotion_justification: "test fixture",
    },
    retrain_mode: "refit_per_fold_fixed_alpha",
    ridge_alpha: 200,
    rmse_stability: {
      dm_hln_pvalue: null,
      dm_hln_statistic: null,
      dm_method: "harvey_leybourne_newbold_1997",
      dm_passes: null,
      rmse_cv: 0.1,
      rmse_max_deviation_pct: 0.2,
      rmse_mean: 3.1,
      rmse_per_fold: [3.2, 3.0, 3.1, 3.1],
    },
    run_date: "2026-06-04T22:57:17Z",
    run_id: "11111111-1111-4111-8111-111111111111",
    schema_version: "1.0.0",
    ...overrides,
  };
}

function mockFetchResponse(body, init = {}) {
  const ok = init.ok ?? true;
  const status = init.status ?? (ok ? 200 : 500);

  globalThis.fetch = vi.fn().mockResolvedValue({
    ok,
    status,
    json: vi.fn().mockResolvedValue(body),
  });
}

describe("TrustStrip", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders model grade, source freshness, and unvalidated state from a typed trust response", async () => {
    mockFetchResponse(trustSurfaceResponse());

    render(<TrustStrip position="QB" />);

    expect(screen.getByRole("status", { name: "Trust strip status" })).toBeTruthy();

    await screen.findByText("EXPERIMENTAL");

    expect(globalThis.fetch).toHaveBeenCalledWith("/api/trust-surface/QB");
    expect(screen.getByText("fantasycalc_native")).toBeTruthy();
    expect(screen.getByText("2025-09-08")).toBeTruthy();
    expect(screen.getByText("Unvalidated")).toBeTruthy();
    expect(
      screen.getByText("QB magnitude predictions carry elevated uncertainty."),
    ).toBeTruthy();
  });

  it("degrades visibly when the trust endpoint returns an error response", async () => {
    mockFetchResponse({ detail: "No artifact" }, { ok: false, status: 404 });

    render(<TrustStrip position="WR" />);

    await screen.findByText("Trust data unavailable");

    expect(screen.queryByText("ACTIVE_B")).toBeNull();
    expect(screen.queryByText("DECISION_GRADE")).toBeNull();
  });

  it("degrades visibly when the trust endpoint cannot be reached", async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error("network down"));

    render(<TrustStrip position="RB" />);

    await screen.findByText("Trust data unavailable");

    expect(screen.queryByText("ACTIVE_B")).toBeNull();
    expect(screen.queryByText("DECISION_GRADE")).toBeNull();
  });

  it("degrades visibly when the 200 response fails generated Zod validation", async () => {
    mockFetchResponse({ overall_grade: "ACTIVE_B" });

    render(<TrustStrip position="TE" />);

    await screen.findByText("Trust data unavailable");

    await waitFor(() => {
      expect(screen.queryByText("ACTIVE_B")).toBeNull();
    });
  });
});
