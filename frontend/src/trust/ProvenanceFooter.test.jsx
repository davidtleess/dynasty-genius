// @vitest-environment jsdom

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

const TRUST_DIR = join(process.cwd(), "src", "trust");
const GRADE_QUALIFIER =
  "internal model grade — not a market-edge or decision-support claim";

function authoredTrustFiles() {
  if (!existsSync(TRUST_DIR)) {
    return [];
  }
  return readdirSync(TRUST_DIR)
    .filter((name) => /\.(css|jsx?|tsx?)$/.test(name))
    .filter((name) => !name.includes(".test."))
    .map((name) => join(TRUST_DIR, name));
}

function provenance(overrides = {}) {
  return {
    git_sha: "abc1234",
    model_artifact_hash: "hash-qb",
    model_version: "engine_b_v2",
    run_date: "2026-05-31T00:00:00Z",
    run_id: "483f87f9-1a16-4750-a825-0165c7335696",
    ...overrides,
  };
}

function market(overrides = {}) {
  return {
    label: "dynastyprocess_ecr_2qb",
    snapshot_dates: { 2020: "2026-05-31", 2021: "2026-05-31" },
    source: "dp_archive",
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

describe("ProvenanceFooter", () => {
  it("renders provenance, market source, snapshots, and the demoted grade qualifier", async () => {
    const { ProvenanceFooter } = await import("./ProvenanceFooter");

    render(
      <ProvenanceFooter
        provenance={provenance()}
        market={market()}
        overallGrade="ACTIVE_B_VALIDATED"
      />,
    );

    const footer = screen.getByRole("contentinfo", { name: "Model trust provenance" });
    for (const text of [
      "483f87f9-1a16-4750-a825-0165c7335696",
      "2026-05-31T00:00:00Z",
      "engine_b_v2",
      "hash-qb",
      "abc1234",
      "dynastyprocess_ecr_2qb",
      "2020: 2026-05-31",
      "2021: 2026-05-31",
      "ACTIVE_B_VALIDATED",
      GRADE_QUALIFIER,
    ]) {
      expect(within(footer).getByText(text)).toBeTruthy();
    }
  });

  it("uses neutral not-available tokens for nullable provenance fields", async () => {
    const { ProvenanceFooter } = await import("./ProvenanceFooter");

    render(
      <ProvenanceFooter
        provenance={provenance({ git_sha: null, run_id: null })}
        market={market({ snapshot_dates: null })}
        overallGrade="ACTIVE_B"
      />,
    );

    const footer = screen.getByRole("contentinfo", { name: "Model trust provenance" });
    expect(within(footer).getAllByText("not available").length).toBeGreaterThanOrEqual(
      2,
    );
  });

  it("uses neutral styling and authored trust wording only", async () => {
    const { ProvenanceFooter } = await import("./ProvenanceFooter");

    const { container } = render(
      <ProvenanceFooter
        provenance={provenance()}
        market={market()}
        overallGrade="ACTIVE_B_VALIDATED"
      />,
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
