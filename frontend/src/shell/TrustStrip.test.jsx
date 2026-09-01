// @vitest-environment jsdom

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TrustStrip } from "./TrustStrip";

const GRADE_QUALIFIER = "our own grade, not a claim that it beats the market";
const TRUST_STRIP_CSS = join(process.cwd(), "src", "shell", "TrustStrip.css");

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
    model_status: "EXPERIMENTAL",
    model_version: "engine_b_v2",
    overall_grade: "EXPERIMENTAL",
    position: "QB",
    promotion_gate: {
      g1_rank_correlation_pass: false,
      g2_rmse_stability_pass: false,
      g3_market_superiority_pass: "deferred",
      g4_divergence_validity_pass: "deferred",
      gate_version: "1.0",
      model_status: "EXPERIMENTAL",
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

    // DG-109: the strip rides every surface, so its two raw values were the
    // last pipeline keys on David's screen. Both facts survive in words — and
    // the Unvalidated badge still keys off the RAW grade below.
    await screen.findByText("Experimental — the checks are not passing");
    expect(screen.queryByText("EXPERIMENTAL")).toBeNull();

    expect(globalThis.fetch).toHaveBeenCalledWith("/api/trust-surface/QB");
    expect(screen.getByText("FantasyCalc, captured the same day")).toBeTruthy();
    expect(screen.queryByText("fantasycalc_native")).toBeNull();
    expect(screen.getByText("2025-09-08")).toBeTruthy();
    expect(screen.getByText("Unvalidated")).toBeTruthy();
    expect(
      screen.getByText("QB magnitude predictions carry elevated uncertainty."),
    ).toBeTruthy();
  });

  it("renders active grades with the non-decision-grade qualifier in the shell strip", async () => {
    mockFetchResponse(
      trustSurfaceResponse({
        experimental: false,
        overall_grade: "ACTIVE_B_VALIDATED",
        promotion_gate: {
          ...trustSurfaceResponse().promotion_gate,
          overall_grade: "ACTIVE_B_VALIDATED",
        },
      }),
    );

    render(<TrustStrip position="WR" />);

    await screen.findByText("In use, ranks well in testing");
    expect(screen.queryByText("ACTIVE_B_VALIDATED")).toBeNull();

    expect(screen.getByText(GRADE_QUALIFIER)).toBeTruthy();
    expect(screen.queryByText("Unvalidated")).toBeNull();
  });

  it("keeps the shell grade visually neutral instead of emphasized as a success tier", () => {
    const css = readFileSync(TRUST_STRIP_CSS, "utf8");
    const gradeRule = css.match(/\.dg-trust__grade\s*\{[^}]*\}/)?.[0] ?? "";

    // DG-115 re-points this at --dg-chrome. The assertion's purpose is
    // unchanged — the grade must not be painted as a success tier — but the
    // old token was model blue, which is a LANE hue on a strip that reports
    // provenance rather than model output. Chrome is achromatic by contract
    // (visualFoundation.test.js), so this is a strictly stronger neutrality
    // claim than the one it replaces, not a relaxation.
    expect(gradeRule).toContain("color: var(--dg-chrome)");
    expect(gradeRule).not.toContain("--dg-model-emphasis");
    expect(gradeRule).not.toContain("--dg-chrome-strong");
    expect(gradeRule).not.toMatch(/var\(--dg-(?:up|down)\)/);
    expect(gradeRule).not.toMatch(/font-weight:\s*600/);
    expect(css).not.toMatch(/(^|[\s,{])\.(?:green|red|pass|success)\b/i);
    expect(css).not.toMatch(new RegExp("ver" + "dict", "i"));
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

  // DG-132 — the strip's accuracy claim is only honest while it describes the model
  // that is actually answering. On 2026-09-01 it described four models replaced the day
  // before and nothing said so: both backend guards compared a version string that reads
  // "engine_b_v2" for every bundle ever built.
  it("says so on screen when the figures describe a model that has been replaced", async () => {
    const note =
      "These accuracy numbers were measured on an earlier version of this model. " +
      "The version answering today has been retrained since.";
    mockFetchResponse(
      trustSurfaceResponse({
        describes_deployed_model: false,
        deployed_model_note: note,
      }),
    );

    render(<TrustStrip position="QB" />);

    expect(await screen.findByText(note)).toBeTruthy();
  });

  it("stays silent when the figures do describe the deployed model", async () => {
    mockFetchResponse(
      trustSurfaceResponse({
        describes_deployed_model: true,
        deployed_model_note: null,
      }),
    );

    render(<TrustStrip position="QB" />);

    await screen.findByText(GRADE_QUALIFIER);

    expect(screen.queryByText(/measured on an earlier version/)).toBeNull();
  });
});
