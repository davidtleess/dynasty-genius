// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TradeLab } from "./TradeLab";

const MITIGATION_COPY =
  "This diagnostic panel does not calculate whether you win or lose this trade, and it does not judge if this transaction fits your team. It keeps the model and market views separate and surfaces stale or unavailable data as caveats, so you can evaluate the numbers yourself.";

describe("TradeLab H1 caveat placement", () => {
  it("consolidates the intro disclaimer and mitigation into one standard caveat block", () => {
    render(<TradeLab />);

    const block = screen.getByRole("note", { name: "Trade Lab caveat" });
    expect(block.textContent).toContain(MITIGATION_COPY);
    expect(block.textContent).toContain("Descriptive only — not decision-grade.");
    expect(block.querySelector("[data-mitigation-contract]")?.textContent).toBe(
      MITIGATION_COPY,
    );
    expect(document.querySelectorAll(".dg-trade-lab__banner")).toHaveLength(0);
    expect(document.querySelectorAll(".dg-trade-lab__mitigation")).toHaveLength(0);
  });
});
