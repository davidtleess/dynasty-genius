// @vitest-environment jsdom

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

const TRUST_DIR = join(process.cwd(), "src", "trust");
const EXPECTED_TRUTH_COPY =
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

function trustViewModel(overrides = {}) {
  return {
    experimental: true,
    folds: [],
    gates: {
      g1_rank_correlation_pass: true,
      g2_rmse_stability_pass: true,
      g3_market_superiority_pass: "deferred",
      g4_divergence_validity_pass: "insufficient_data",
      overall_grade: "EXPERIMENTAL",
      promotion_justification: "CIs include zero.",
    },
    market: {
      label: "dynastyprocess_ecr_2qb",
      snapshot_dates: { 2021: "2021-09-08" },
      source: "dp_archive",
    },
    model_card: null,
    model_reliability: null,
    overall_grade: "ACTIVE_B_VALIDATED",
    position: "WR",
    provenance: {
      git_sha: "12f55658",
      model_artifact_hash: "hash-wr",
      model_version: "engine_b_v2",
      run_date: "2026-05-31T00:00:00Z",
      run_id: "fc1e6e1c-180a-4c0b-b93b-cb525ef404f1",
    },
    ...overrides,
  };
}

describe("TrustTruthPanel", () => {
  it("renders the canonical G3 truth copy without a global R2 claim", async () => {
    const { TRUST_TRUTH_COPY, TrustTruthPanel } = await import("./TrustTruthPanel");

    expect(TRUST_TRUTH_COPY).toBe(EXPECTED_TRUTH_COPY);

    render(<TrustTruthPanel vm={trustViewModel()} />);

    const panel = screen.getByRole("region", { name: "Model trust truth" });
    expect(within(panel).getByText(EXPECTED_TRUTH_COPY)).toBeTruthy();
    expect(within(panel).queryByText(/R²|R2|r2/i)).toBeNull();
  });

  it("shows non-dismissible decision support and experimental state", async () => {
    const { TrustTruthPanel } = await import("./TrustTruthPanel");

    render(<TrustTruthPanel vm={trustViewModel()} />);

    const panel = screen.getByRole("region", { name: "Model trust truth" });
    expect(within(panel).getByText("decision_supported = false")).toBeTruthy();
    expect(within(panel).queryByRole("button", { name: /dismiss/i })).toBeNull();
    expect(within(panel).getByText("Experimental — not validated")).toBeTruthy();
  });

  it("demotes overall grade out of the truth panel", async () => {
    const { TrustTruthPanel } = await import("./TrustTruthPanel");

    const { container } = render(<TrustTruthPanel vm={trustViewModel()} />);
    const panel = screen.getByRole("region", { name: "Model trust truth" });

    expect(within(panel).getByText(EXPECTED_TRUTH_COPY)).toBeTruthy();
    expect(within(panel).queryByText("ACTIVE_B_VALIDATED")).toBeNull();
    expect(within(panel).queryByText("ACTIVE_B")).toBeNull();
    expect(within(panel).queryByText("EXPERIMENTAL")).toBeNull();
    expect(within(panel).queryByText(/internal model grade/i)).toBeNull();
    expect(container.querySelector('[class*="badge"]')).toBeNull();
    expect(container.querySelector('[class*="success"]')).toBeNull();
  });

  it("does not add prohibited conclusion identifiers or status styling", () => {
    const authoredText = authoredTrustFiles()
      .map((path) => readFileSync(path, "utf8"))
      .join("\n");

    expect(authoredText).not.toMatch(new RegExp("ver" + "dict", "i"));
    expect(authoredText).not.toMatch(/\.(?:green|red|pass|success)\b/i);
    expect(authoredText).not.toMatch(/[✓✔✅]/);
  });
});
