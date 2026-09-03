// @vitest-environment jsdom
//
// DG-144 (2026-09-03) — one number per player, on David's own roster.
//
// His ruling: "plus or minus 20, remove it, one number per player." The range
// DG-128 printed under the value was a per-position constant — two sigma_B, so
// QB 44.8 / RB 45.6 / WR 40.0 / TE 47.2 — describing the position's model error,
// never the player. The API still ships `dvs_band_low` / `dvs_band_high`; the
// screen no longer reads them. The basis marker (`data-basis`) is unchanged:
// David ruled on 2026-09-01 that nothing greys or lightens the number by its
// basis, and the marker stays a fact, not a style hook.
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { activeAudit } from "./fixtures";
import { RosterAuditTable } from "./RosterAuditTable";

function rowFor(name) {
  return within(screen.getByRole("table"))
    .getAllByRole("row")
    .find((row) => within(row).queryByText(name));
}

describe("the roster table shows one number per player", () => {
  it("prints the measured value with no range under it, and still marks the cell measured", () => {
    render(<RosterAuditTable players={activeAudit().players} />);
    const row = rowFor("Active WR");
    expect(within(row).getByText("78.5 (81%)")).toBeTruthy();
    // The fixture carries a band (58.5 to 98.5) exactly as the API ships it;
    // none of it reaches the row.
    expect(within(row).queryByText(/range/i)).toBeNull();
    expect(within(row).queryByText(/59 to 99/)).toBeNull();
    expect(row.querySelector(".dg-roster__band")).toBeNull();
    expect(row.querySelector("[data-basis]").getAttribute("data-basis")).toBe("B");
  });

  it("prints a blended value just as bare, and still marks the cell a blend", () => {
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
    expect(within(row).getByText("63.8 (81%)")).toBeTruthy();
    expect(within(row).queryByText(/range/i)).toBeNull();
    expect(within(row).queryByText(/30 to 98/)).toBeNull();
    expect(row.querySelector(".dg-roster__band")).toBeNull();
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
    expect(row.querySelector(".dg-roster__band")).toBeNull();
    expect(row.querySelector("[data-basis]").getAttribute("data-basis")).toBe("");
  });
});
