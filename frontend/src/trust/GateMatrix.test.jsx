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

function gates(overrides = {}) {
  return {
    g1_rank_correlation_pass: true,
    g2_rmse_stability_pass: false,
    g3_market_superiority_pass: "deferred",
    g4_divergence_validity_pass: "insufficient_data",
    overall_grade: "EXPERIMENTAL",
    promotion_justification: "CIs include zero; MET is not decision support.",
    ...overrides,
  };
}

function expectGate(panel, label, status) {
  expect(within(panel).getByText(`${label}: ${status}`)).toBeTruthy();
}

describe("GateMatrix", () => {
  it("maps boolean and deferred gate fields into neutral labels", async () => {
    const { GateMatrix } = await import("./GateMatrix");

    render(<GateMatrix gates={gates()} />);

    const matrix = screen.getByRole("region", { name: "Validation gates" });
    expectGate(matrix, "G1 Rank correlation", "MET");
    expectGate(matrix, "G2 RMSE stability", "UNMET");
    expectGate(matrix, "G3 Market superiority", "DEFERRED");
    expectGate(matrix, "G4 Divergence validity", "INSUFFICIENT DATA");
  });

  it("covers the G3 and G4 true/false/deferred state space", async () => {
    const { GateMatrix } = await import("./GateMatrix");
    const { rerender } = render(
      <GateMatrix
        gates={gates({
          g3_market_superiority_pass: true,
          g4_divergence_validity_pass: true,
        })}
      />,
    );

    let matrix = screen.getByRole("region", { name: "Validation gates" });
    expectGate(matrix, "G3 Market superiority", "MET");
    expectGate(matrix, "G4 Divergence validity", "MET");

    rerender(
      <GateMatrix
        gates={gates({
          g3_market_superiority_pass: false,
          g4_divergence_validity_pass: false,
        })}
      />,
    );
    matrix = screen.getByRole("region", { name: "Validation gates" });
    expectGate(matrix, "G3 Market superiority", "UNMET");
    expectGate(matrix, "G4 Divergence validity", "UNMET");

    rerender(
      <GateMatrix
        gates={gates({
          g3_market_superiority_pass: "deferred",
          g4_divergence_validity_pass: "deferred",
        })}
      />,
    );
    matrix = screen.getByRole("region", { name: "Validation gates" });
    expectGate(matrix, "G3 Market superiority", "DEFERRED");
    expectGate(matrix, "G4 Divergence validity", "DEFERRED");
  });

  it("frames MET as point-estimate state, not decision support", async () => {
    const { GateMatrix } = await import("./GateMatrix");

    render(
      <GateMatrix
        gates={gates({
          g1_rank_correlation_pass: true,
          g2_rmse_stability_pass: true,
          g3_market_superiority_pass: true,
          g4_divergence_validity_pass: true,
          promotion_justification: "WR point-rule pass; CIs include zero.",
        })}
      />,
    );

    const matrix = screen.getByRole("region", { name: "Validation gates" });
    expectGate(matrix, "G3 Market superiority", "MET");
    expect(
      within(matrix).getByText("MET = point-estimate gate state, not decision support"),
    ).toBeTruthy();
    expect(within(matrix).getByText(/CIs include zero/i)).toBeTruthy();
    expect(within(matrix).queryByText(/proven edge|validated win/i)).toBeNull();
  });

  it("uses neutral styling only for gates", async () => {
    const { GateMatrix } = await import("./GateMatrix");

    const { container } = render(<GateMatrix gates={gates()} />);
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
