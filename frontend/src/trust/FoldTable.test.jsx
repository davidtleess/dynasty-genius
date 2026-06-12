// @vitest-environment jsdom

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

const TRUST_DIR = join(process.cwd(), "src", "trust");

function authoredTrustFiles() {
  if (!existsSync(TRUST_DIR)) {
    return [];
  }
  return readdirSync(TRUST_DIR)
    .filter((name) => /\.(css|jsx?|tsx?)$/.test(name))
    .filter((name) => !name.includes(".test."))
    .map((name) => join(TRUST_DIR, name));
}

function fold(overrides = {}) {
  return {
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
    ...overrides,
  };
}

function tableRows(table) {
  return within(table).getAllByRole("row").slice(1);
}

function expectRowText(row, text) {
  expect(row.textContent).toContain(text);
}

describe("FoldTable", () => {
  it("renders a semantic table with one formatted row per fold", async () => {
    const { FoldTable } = await import("./FoldTable");

    render(
      <FoldTable
        folds={[
          fold(),
          fold({
            fold_index: 2,
            train_years: [2019, 2020],
            test_year: 2021,
            n_train: 138,
            n_test: 41,
            kendall_tau: 0.12,
            kendall_tau_bca_ci95: [0.05, 0.18],
            spearman_rho: 0.16,
            spearman_rho_bca_ci95: [0.07, 0.22],
            rank_ic: 0.16,
            rmse: 4.12,
            mae: 3.05,
          }),
        ]}
      />,
    );

    const table = screen.getByRole("table", { name: "Per-fold backtest results" });
    for (const header of [
      "Fold",
      "Train years",
      "Test year",
      "N train",
      "N test",
      "Kendall tau",
      "Kendall CI95",
      "Spearman rho",
      "Spearman CI95",
      "Rank IC",
      "RMSE",
      "MAE",
      "CI note",
    ]) {
      expect(within(table).getByRole("columnheader", { name: header })).toBeTruthy();
    }

    const [firstRow, secondRow] = tableRows(table);
    for (const text of [
      "Fold 1",
      "2018, 2019",
      "2020",
      "120",
      "34",
      "0.18",
      "[-0.03, 0.31]",
      "0.24",
      "[-0.01, 0.42]",
      "3.80",
      "2.90",
    ]) {
      expectRowText(firstRow, text);
    }

    for (const text of [
      "Fold 2",
      "2019, 2020",
      "2021",
      "138",
      "41",
      "0.12",
      "[0.05, 0.18]",
      "0.16",
      "[0.07, 0.22]",
      "4.12",
      "3.05",
    ]) {
      expectRowText(secondRow, text);
    }
  });

  it("marks only folds whose Kendall or Spearman CI95 includes zero", async () => {
    const { FoldTable } = await import("./FoldTable");

    render(
      <FoldTable
        folds={[
          fold({ fold_index: 1, kendall_tau_bca_ci95: [-0.04, 0.2] }),
          fold({
            fold_index: 2,
            kendall_tau_bca_ci95: [0.03, 0.2],
            spearman_rho_bca_ci95: [0.04, 0.3],
          }),
          fold({
            fold_index: 3,
            kendall_tau_bca_ci95: [0.03, 0.2],
            spearman_rho_bca_ci95: [-0.02, 0.3],
          }),
        ]}
      />,
    );

    const table = screen.getByRole("table", { name: "Per-fold backtest results" });
    const [kendallSpanRow, strictAwayRow, spearmanSpanRow] = tableRows(table);

    expectRowText(kendallSpanRow, "CI includes zero");
    expect(strictAwayRow.textContent).not.toContain("CI includes zero");
    expectRowText(spearmanSpanRow, "CI includes zero");
  });

  it("renders a neutral empty state when no folds are available", async () => {
    const { FoldTable } = await import("./FoldTable");

    render(<FoldTable folds={[]} />);

    expect(screen.getByText("No fold data")).toBeTruthy();
    expect(
      screen.queryByRole("table", { name: "Per-fold backtest results" }),
    ).toBeNull();
  });

  it("uses neutral styling and authored trust wording only", async () => {
    const { FoldTable } = await import("./FoldTable");

    const { container } = render(<FoldTable folds={[fold()]} />);
    const authoredText = authoredTrustFiles()
      .map((path) => readFileSync(path, "utf8"))
      .join("\n");

    expect(container.querySelector('[class*="green"]')).toBeNull();
    expect(container.querySelector('[class*="red"]')).toBeNull();
    expect(container.querySelector('[class*="pass"]')).toBeNull();
    expect(container.querySelector('[class*="success"]')).toBeNull();
    expect(container.querySelector('[class*="badge"]')).toBeNull();
    expect(container.textContent).not.toMatch(/[✓✔✅]/);
    expect(authoredText).not.toMatch(new RegExp("ver" + "dict", "i"));
    expect(authoredText).not.toMatch(/(^|[\s,{])\.(?:green|red|pass|success)\b/i);
    expect(authoredText).not.toMatch(/[✓✔✅]/);
  });
});
