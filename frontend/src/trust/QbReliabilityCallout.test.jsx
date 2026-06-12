// @vitest-environment jsdom

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { render, screen } from "@testing-library/react";
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

function reliability(overrides = {}) {
  return {
    caveat: "QB magnitude predictions carry elevated uncertainty.",
    position: "QB",
    r2_oos_mean: 0.14,
    spearman_rho_mean: 0.31,
    ...overrides,
  };
}

function expectNeutralAuthoredTrustFiles() {
  const authoredText = authoredTrustFiles()
    .map((path) => readFileSync(path, "utf8"))
    .join("\n");

  expect(authoredText).not.toMatch(new RegExp("ver" + "dict", "i"));
  expect(authoredText).not.toMatch(/(^|[\s,{])\.(?:green|red|pass|success)\b/i);
  expect(authoredText).not.toMatch(/[✓✔✅]/);
}

describe("QbReliabilityCallout", () => {
  it("renders QB reliability as elevated uncertainty with real figures", async () => {
    const { QbReliabilityCallout } = await import("./QbReliabilityCallout");

    render(<QbReliabilityCallout position="QB" reliability={reliability()} />);

    expect(screen.getByRole("region", { name: "QB reliability note" })).toBeTruthy();
    expect(screen.getByText("Elevated uncertainty")).toBeTruthy();
    expect(
      screen.getByText("QB magnitude predictions carry elevated uncertainty."),
    ).toBeTruthy();
    expect(screen.getByText("OOS R2: 0.14")).toBeTruthy();
    expect(screen.getByText("Spearman: 0.31")).toBeTruthy();
  });

  it("renders not-available tokens without fabricating null figures", async () => {
    const { QbReliabilityCallout } = await import("./QbReliabilityCallout");

    render(
      <QbReliabilityCallout
        position="QB"
        reliability={reliability({ r2_oos_mean: null, spearman_rho_mean: null })}
      />,
    );

    expect(screen.getByText("OOS R2: not available")).toBeTruthy();
    expect(screen.getByText("Spearman: not available")).toBeTruthy();
  });

  it("renders nothing for non-QB positions or missing reliability", async () => {
    const { QbReliabilityCallout } = await import("./QbReliabilityCallout");

    const nonQb = render(
      <QbReliabilityCallout position="RB" reliability={reliability()} />,
    );
    expect(nonQb.container.textContent).toBe("");
    nonQb.unmount();

    const missing = render(<QbReliabilityCallout position="QB" reliability={null} />);
    expect(missing.container.textContent).toBe("");
  });

  it("uses neutral styling and authored trust wording only", async () => {
    const { QbReliabilityCallout } = await import("./QbReliabilityCallout");

    const { container } = render(
      <QbReliabilityCallout position="QB" reliability={reliability()} />,
    );

    expect(container.querySelector('[class*="green"]')).toBeNull();
    expect(container.querySelector('[class*="red"]')).toBeNull();
    expect(container.querySelector('[class*="pass"]')).toBeNull();
    expect(container.querySelector('[class*="success"]')).toBeNull();
    expect(container.querySelector('[class*="badge"]')).toBeNull();
    expect(container.textContent).not.toMatch(/[✓✔✅]/);
    expectNeutralAuthoredTrustFiles();
  });
});
