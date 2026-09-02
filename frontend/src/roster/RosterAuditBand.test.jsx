// @vitest-environment jsdom
//
// DG-128 (2026-09-01) — the band ships with the number, on David's own roster.
//
// His ruling: "A prior-dominated estimate must not render with the same
// authority as a measured one." The range printed under the value carries that
// — a prior-touched number's range is wider. The value cell also rides a basis
// marker (`data-basis`); David ruled the same evening that nothing greys or
// lightens the number by its basis, so the marker is a fact, not a style hook.
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { fieldLabel } from "../lib/copy";
import { activeAudit } from "./fixtures";
import { RosterAuditTable } from "./RosterAuditTable";

function rowFor(name) {
  return within(screen.getByRole("table"))
    .getAllByRole("row")
    .find((row) => within(row).queryByText(name));
}

describe("the roster table and the band", () => {
  it("prints the range under a measured value and marks the cell measured", () => {
    render(<RosterAuditTable players={activeAudit().players} />);
    const row = rowFor("Active WR");
    expect(within(row).getByText("78.5 (81%)")).toBeTruthy();
    // 78.5 ± 20.0 (WR sigma_B), whole points on screen, under the label the
    // player card gives the same pair — one phrase, from the dictionary.
    expect(within(row).getByText("Likely range 59 to 99")).toBeTruthy();
    expect(fieldLabel("dvs_band_low")).toBe("Likely range");
    expect(row.querySelector("[data-basis]").getAttribute("data-basis")).toBe("B");
  });

  it("prints the wider range under a blended value and marks the cell a blend", () => {
    const [measured] = activeAudit().players;
    const blended = {
      ...measured,
      player_id: "p-blend",
      full_name: "Short-Sample WR",
      dvs_engine: "blend",
      dynasty_value_score: 63.8,
      dvs_band_low: 30.1,
      dvs_band_high: 97.5,
      caveats: ["engine_ab_blend_low_sample:games=6"],
    };
    render(<RosterAuditTable players={[measured, blended]} />);
    const row = rowFor("Short-Sample WR");
    expect(within(row).getByText("Likely range 30 to 98")).toBeTruthy();
    expect(row.querySelector("[data-basis]").getAttribute("data-basis")).toBe("blend");
  });

  it("prints no range and no basis for a player with no number", () => {
    const [measured] = activeAudit().players;
    const unscored = {
      ...measured,
      player_id: "p-none",
      full_name: "Unscored TE",
      dvs_engine: null,
      dynasty_value_score: null,
      dvs_pct: null,
      dvs_band_low: null,
      dvs_band_high: null,
    };
    render(<RosterAuditTable players={[unscored]} />);
    const row = rowFor("Unscored TE");
    expect(within(row).queryByText(/range/i)).toBeNull();
    expect(row.querySelector("[data-basis]").getAttribute("data-basis")).toBe("");
  });
});
