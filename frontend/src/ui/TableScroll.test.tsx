// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TableScroll } from "./TableScroll";

// DG-117 panel finding: this primitive was the one component in src/ui with no
// test of its own, asserted only sideways through three consumers. The next
// surface that reaches for it inherits whatever it does, so its own contract is
// pinned here. The CSS half — the `overflow-x` rule and the shell's
// `min-inline-size: 0`, which is what makes the rule able to act at all — is
// pinned in uiCssContract.test.js, where the stylesheets are already read.
describe("TableScroll", () => {
  it("is a named region a keyboard reader can land in", () => {
    render(
      <TableScroll label="Per-fold backtest results">
        <table>
          <tbody>
            <tr>
              <td>7.3</td>
            </tr>
          </tbody>
        </table>
      </TableScroll>,
    );

    const region = screen.getByRole("region", { name: "Per-fold backtest results" });
    expect(region.tagName).toBe("SECTION");
    // A scroll container reachable only by dragging is a region a keyboard user
    // cannot read (axe scrollable-region-focusable).
    expect(region.getAttribute("tabindex")).toBe("0");
    expect(region.className).toContain("dg-table-scroll");
    // The table goes inside it, unchanged.
    expect(region.querySelector("table")).not.toBeNull();
  });
});
