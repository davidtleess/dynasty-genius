// @vitest-environment jsdom
//
// DG-146 (2026-09-03) — a small rookie marker on the roster row.
//
// David, 23:35 ET, answering whether the roster table should get a marker back
// now that DG-144 removed the range that used to make a rookie-model number
// look different from a measured one: "small marker indicating theyre a rookie."
// The word is keyed on the player fact (`is_prospect`), not on the model basis;
// the number itself is untouched — his 2026-09-01 ruling that nothing greys or
// lightens the value by its basis still stands.
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ROOKIE_MARKER } from "../lib/copy";
import { activeAudit } from "./fixtures";
import { RosterAuditTable } from "./RosterAuditTable";

function rowFor(name) {
  return within(screen.getByRole("table"))
    .getAllByRole("row")
    .find((row) => within(row).queryByText(name));
}

describe("the roster table marks rookies", () => {
  it("prints one small word next to a rookie's name and nothing next to a veteran's", () => {
    const [veteran] = activeAudit().players;
    const rookie = {
      ...veteran,
      player_id: "p-rookie",
      sleeper_id: "r-1",
      full_name: "Rookie WR",
      is_prospect: true,
      draft_class: 2026,
      dvs_engine: "A",
      dynasty_value_score: 61.6,
    };
    render(<RosterAuditTable players={[veteran, rookie]} />);

    const rookieRow = rowFor("Rookie WR");
    const mark = rookieRow.querySelector(".dg-roster__rookie");
    expect(mark).not.toBeNull();
    expect(mark.textContent).toBe(ROOKIE_MARKER);
    expect(ROOKIE_MARKER).toBe("Rookie");
    // The number is untouched: same cell, same basis marker, no extra styling hook.
    expect(rookieRow.querySelector("[data-basis]").getAttribute("data-basis")).toBe(
      "A",
    );
    expect(within(rookieRow).getByText("61.6 (81%)")).toBeTruthy();

    const veteranRow = rowFor("Active WR");
    expect(veteranRow.querySelector(".dg-roster__rookie")).toBeNull();
    expect(within(veteranRow).queryByText(/rookie/i)).toBeNull();
  });

  it("does not mark a short-sample veteran whose number is a blend — he is not a rookie", () => {
    const [veteran] = activeAudit().players;
    const blended = {
      ...veteran,
      player_id: "p-blend",
      full_name: "Short-Sample WR",
      is_prospect: false,
      dvs_engine: "blend",
      caveats: ["engine_ab_blend_low_sample:games=6"],
    };
    render(<RosterAuditTable players={[blended]} />);
    const row = rowFor("Short-Sample WR");
    expect(row.querySelector(".dg-roster__rookie")).toBeNull();
    expect(row.querySelector("[data-basis]").getAttribute("data-basis")).toBe("blend");
  });
});
