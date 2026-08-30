// @vitest-environment jsdom

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TradeLab } from "./TradeLab";

// DG-111 — trade_lab_fe_mitigation_v1 replacement copy. David's 2026-08-29
// ruling is the sign-off that released the byte lock; the replacement is
// recorded verbatim in the ticket. Every fact the lock protected survives:
// no win/lose verdict is computed, fit is not judged, the two pricings stay
// separate rather than blended, a stale or missing price says so in its own
// lane, and the call is the manager's. Only the register changed.
const MITIGATION_COPY =
  "We price both sides two ways — what the dynasty market is paying, and what our model says — and keep the two apart instead of blending them into one number. Where a price is stale or missing, that lane says so. We don't call the winner and we don't judge whether the deal fits your team: that part is yours.";

describe("TradeLab H1 caveat placement", () => {
  it("consolidates the intro disclaimer and mitigation into one standard caveat block", () => {
    render(<TradeLab />);

    const block = screen.getByRole("note", { name: "Trade Lab caveat" });
    expect(block.textContent).toContain(MITIGATION_COPY);
    // The stamp under the paragraph is retired with the paragraph itself.
    expect(block.textContent).not.toContain("Descriptive only — not decision-grade.");
    expect(block.querySelector("[data-mitigation-contract]")?.textContent).toBe(
      MITIGATION_COPY,
    );
    expect(document.querySelectorAll(".dg-trade-lab__banner")).toHaveLength(0);
    expect(document.querySelectorAll(".dg-trade-lab__mitigation")).toHaveLength(0);
  });
});
