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

  it("keeps SpreadBar model and market lane tokens isolated", () => {
    const css = readUiCss();
    const marketLane = css.match(
      /\.dg-ui-spread\[data-lane="market"\][\s\S]{0,500}/,
    );
    const modelLane = css.match(/\.dg-ui-spread\[data-lane="model"\][\s\S]{0,500}/);

    expect(marketLane, "market lane CSS block missing").not.toBeNull();
    expect(modelLane, "model lane CSS block missing").not.toBeNull();
    expect(marketLane?.[0]).toContain("--dg-market");
    expect(marketLane?.[0]).not.toContain("--dg-model");
    expect(modelLane?.[0]).toContain("--dg-model");
    expect(modelLane?.[0]).not.toContain("--dg-market");
  });

  it("keeps team colors identity-only and out of row backgrounds/status lanes", () => {
    const css = readUiCss();

    expect(css).toContain("dg-ui-player-id__team-mark");
    expect(css).not.toMatch(/background(?:-color)?:\s*var\(--dg-team/i);
    expect(css).not.toMatch(/\.dg-ui-[^{]*(status|delta|market|model)[^{]*--team/i);
    expect(css).not.toMatch(/border-left:\s*(?:2|3|4|5|6|7|8|9)\d*px/i);
  });
});
