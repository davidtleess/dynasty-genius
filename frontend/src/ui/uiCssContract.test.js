import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const uiDir = dirname(fileURLToPath(import.meta.url));
const uiCssPath = resolve(uiDir, "ui.css");

function readUiCss() {
  return readFileSync(uiCssPath, "utf8");
}

describe("DG primitive CSS contract", () => {
  it("uses semantic tokens and the shared focus grammar from day one", () => {
    const css = readUiCss();
    const withoutVarUsages = css.replace(/var\(--dg-[a-z0-9-]+(?:,[^)]+)?\)/g, "");

    expect(css).toContain("--dg-focus");
    expect(css).toMatch(/:focus-visible\s*\{/);
    expect(css).toContain("outline");
    expect(css).toContain("font-variant-numeric: tabular-nums");
    expect(css).toContain("text-align: right");
    expect(withoutVarUsages).not.toMatch(/#[0-9a-f]{3,8}\b/i);
    expect(withoutVarUsages).not.toMatch(/\boklch\(/i);
    expect(withoutVarUsages).not.toMatch(/\brgba?\(/i);
  });
});
