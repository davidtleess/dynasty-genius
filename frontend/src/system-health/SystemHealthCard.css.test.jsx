import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const SYSTEM_HEALTH_CSS = join(
  process.cwd(),
  "src",
  "system-health",
  "SystemHealthCard.css",
);

describe("SystemHealthCard CSS source guard", () => {
  it("does not use market tokens or positive and stoplight status words", () => {
    const css = readFileSync(SYSTEM_HEALTH_CSS, "utf8");

    expect(css).not.toContain("--dg-market");
    expect(css).not.toMatch(/\b(?:green|red|success|pass)\b/i);
  });
});
