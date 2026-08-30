// @vitest-environment jsdom

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

const TRUST_DIR = join(process.cwd(), "src", "trust");
// DG-111 — the same three facts, said in David's language, none of them
// softened: tied with expert consensus (not ahead), no proven edge (the
// measured difference could be zero), therefore a second opinion. The
// bootstrap-CI evidence that used to be quoted here lives in the study on this
// same surface (FoldTable / GateMatrix), which is where an NDCG diff belongs.
const EXPECTED_TRUTH_COPY =
  "Honest read: our model ranks players about as well as expert consensus — " +
  "DynastyProcess's 2QB rankings, which is what we measure it against — but it " +
  "has not proven it beats them. Season by season across our test years, the " +
  "range around its ranking-quality edge still includes zero.";

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

  // DG-111: "decision_supported = false" was a raw backend field name rendered
  // at the user, and "Experimental — not validated" was a stamp. Both states
  // survive as sentences, still non-dismissible.
  it("states the decision-support and unvalidated states in prose, non-dismissibly", async () => {
    const { TRUST_UNVALIDATED_COPY, TrustTruthPanel } = await import(
      "./TrustTruthPanel"
    );

    render(<TrustTruthPanel vm={trustViewModel()} />);

    const panel = screen.getByRole("region", { name: "Model trust truth" });
    // DG-111: was `decision_supported = false` — a raw backend field name
    // rendered at the user. The state is unchanged and still non-dismissible;
    // it is now the product's one shared model-standing sentence.
    expect(within(panel).queryByText("decision_supported = false")).toBeNull();
    expect(within(panel).queryByText("Descriptive only — not decision-grade.")).toBeNull();
    expect(within(panel).getByTestId("model-standing").textContent).toMatch(
      /second opinion/i,
    );
    expect(within(panel).getByTestId("model-standing").textContent).toMatch(
      /not a proven market-beater/i,
    );
    expect(within(panel).queryByRole("button", { name: /dismiss/i })).toBeNull();
    expect(within(panel).getByText(TRUST_UNVALIDATED_COPY)).toBeTruthy();
    expect(TRUST_UNVALIDATED_COPY).toMatch(/not a track record/i);
  });

  it("demotes overall grade out of the truth panel", async () => {
    const { TrustTruthPanel } = await import("./TrustTruthPanel");

    const { container } = render(<TrustTruthPanel vm={trustViewModel()} />);
    const panel = screen.getByRole("region", { name: "Model trust truth" });

    expect(within(panel).getByText(EXPECTED_TRUTH_COPY)).toBeTruthy();
    expect(within(panel).queryByText("ACTIVE_B_VALIDATED")).toBeNull();
    expect(within(panel).queryByText("ACTIVE_B")).toBeNull();
    expect(within(panel).queryByText("EXPERIMENTAL")).toBeNull();
    expect(within(panel).queryByText("Experimental — not validated")).toBeNull();
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
