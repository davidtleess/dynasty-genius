import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const dailyCssPath = resolve(
  dirname(fileURLToPath(import.meta.url)),
  "DailyWhatChanged.css",
);

describe("DailyWhatChanged I2a CSS contract", () => {
  it("pins daily-open density, tabular values, display font, and reduced motion", () => {
    const css = readFileSync(dailyCssPath, "utf8");

    expect(css).toMatch(/\.dg-wc__player-row[\s\S]*\b(?:min-)?height:\s*32px/);
    expect(css).toMatch(/font-family:\s*var\(--dg-font-display/);
    expect(css).toMatch(/@media\s*\(\s*prefers-reduced-motion:\s*reduce\s*\)/);
    expect(css).toMatch(/animation:\s*none/);
  });
});
