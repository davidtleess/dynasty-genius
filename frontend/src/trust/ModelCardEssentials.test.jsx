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

function modelCard() {
  return {
    backtest_run_id: "483f87f9-1a16-4750-a825-0165c7335696",
    caveats: ["Decision support remains disabled.", "Small cohorts can be unstable."],
    generated_at: "2026-06-10T00:00:00Z",
    intended_use: "Read-only trust review for model validation context.",
    is_experimental: true,
    known_failure_modes: [
      "Quarterback magnitude estimates carry elevated uncertainty.",
      "Market-superiority intervals include zero.",
    ],
    out_of_scope_uses: [
      "Roster-action recommendations",
      "Trade execution without separate evidence review",
    ],
    position: "QB",
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

describe("ModelCardEssentials", () => {
  it("renders the curated model-card essentials with full text", async () => {
    const { ModelCardEssentials } = await import("./ModelCardEssentials");

    render(<ModelCardEssentials card={modelCard()} />);

    const section = screen.getByRole("region", { name: "Model card essentials" });
    expect(
      within(section).getByText("Read-only trust review for model validation context."),
    ).toBeTruthy();
    for (const text of [
      "Roster-action recommendations",
      "Trade execution without separate evidence review",
      "Decision support remains disabled.",
      "Small cohorts can be unstable.",
      "Quarterback magnitude estimates carry elevated uncertainty.",
      "Market-superiority intervals include zero.",
    ]) {
      expect(within(section).getByText(text)).toBeTruthy();
    }
  });

  it("owns the missing-card degradation message", async () => {
    const { ModelCardEssentials } = await import("./ModelCardEssentials");

    render(<ModelCardEssentials card={null} />);

    expect(screen.getByText("Model card unavailable")).toBeTruthy();
  });

  it("uses neutral styling and authored trust wording only", async () => {
    const { ModelCardEssentials } = await import("./ModelCardEssentials");

    const { container } = render(<ModelCardEssentials card={modelCard()} />);

    expect(container.querySelector('[class*="green"]')).toBeNull();
    expect(container.querySelector('[class*="red"]')).toBeNull();
    expect(container.querySelector('[class*="pass"]')).toBeNull();
    expect(container.querySelector('[class*="success"]')).toBeNull();
    expect(container.querySelector('[class*="badge"]')).toBeNull();
    expect(container.textContent).not.toMatch(/[✓✔✅]/);
    expectNeutralAuthoredTrustFiles();
  });
});
