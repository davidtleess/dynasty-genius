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
    const marketLane = css.match(/\.dg-ui-spread\[data-lane="market"\][\s\S]{0,500}/);
    const modelLane = css.match(/\.dg-ui-spread\[data-lane="model"\][\s\S]{0,500}/);

    expect(marketLane, "market lane CSS block missing").not.toBeNull();
    expect(modelLane, "model lane CSS block missing").not.toBeNull();
    expect(marketLane?.[0]).toContain("--dg-market");
    expect(marketLane?.[0]).not.toContain("--dg-model");
    expect(modelLane?.[0]).toContain("--dg-model");
    expect(modelLane?.[0]).not.toContain("--dg-market");
  });

  // DG-117: the containment this ticket is about is two CSS lines, and a panel
  // finding was that nothing pinned either of them. Both look like strays and
  // both are load-bearing, so deleting one has to fail a test rather than
  // quietly return the page to scrolling sideways.
  it("keeps a wide table's overflow inside its own scroller", () => {
    expect(readUiCss()).toMatch(/\.dg-table-scroll\s*\{[^}]*overflow-x:\s*auto/);
  });

  it("keeps the shell's main column able to shrink below its content", () => {
    // A grid ITEM defaults to `min-width: auto` — "never smaller than my
    // content" — so a 1039px table pushed the whole shell wider and every
    // `overflow-x` rule inside it was inert. Wrapping the tables alone took
    // Model Trust from 665px of sideways scroll to 218px; this line took it
    // to 0.
    const shellCss = readFileSync(resolve(uiDir, "../shell/AppShell.css"), "utf8");
    const block = shellCss.match(/\.dg-shell__main\s*\{[^}]*\}/);
    expect(block, ".dg-shell__main rule missing").not.toBeNull();
    expect(block?.[0]).toMatch(/min-inline-size:\s*0/);
  });

  // The receipt panel is anchored to its trigger, so at 390px it opened past
  // the right edge and took the document 158px sideways (Daily What-Changed,
  // measured in Chromium). ReceiptTrigger measures and shifts it back; this is
  // the half that keeps it narrower than the phone in the first place.
  it("keeps an open receipt panel narrower than the viewport", () => {
    const panel = readUiCss().match(/\.dg-ui-receipt__panel\s*\{[^}]*\}/);
    expect(panel, ".dg-ui-receipt__panel rule missing").not.toBeNull();
    expect(panel?.[0]).toMatch(/max-inline-size:\s*calc\(100vw/);
    expect(panel?.[0]).toMatch(/overflow-wrap:\s*anywhere/);
  });

  it("keeps team colors identity-only and out of row backgrounds/status lanes", () => {
    const css = readUiCss();

    expect(css).toContain("dg-ui-player-id__team-mark");
    expect(css).not.toMatch(/background(?:-color)?:\s*var\(--dg-team/i);
    expect(css).not.toMatch(/\.dg-ui-[^{]*(status|delta|market|model)[^{]*--team/i);
    expect(css).not.toMatch(/border-left:\s*(?:2|3|4|5|6|7|8|9)\d*px/i);
  });
});
