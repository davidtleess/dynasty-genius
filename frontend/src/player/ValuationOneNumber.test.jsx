// @vitest-environment jsdom
//
// DG-144 (2026-09-03) — one number per player on the player card too. David:
// "plus or minus 20, remove it, one number per player." The "Likely range" fact
// DG-128 added is gone; "Scored by" still names what PRODUCED the score (the
// basis), and the basis marker still rides the value.
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ValuationTwoLane } from "./ValuationTwoLane";

const market = { caveats: [], status: "unavailable" };
const divergence = { delta: null, status: "unavailable" };

function lane() {
  return screen.getByTestId("player-model-lane");
}

function fact(label) {
  const dt = within(lane()).getByText(label);
  return dt.nextElementSibling.textContent;
}

function renderModel(model) {
  render(<ValuationTwoLane model={model} market={market} divergence={divergence} />);
}

describe("the player card shows one number per player", () => {
  it("prints the value and its basis with no range fact, even though the API carries a band", () => {
    renderModel({
      engine_path: "BLEND_AB",
      dvs_engine: "blend",
      model_grade: "ACTIVE_B",
      model_version: "engine_b_v2",
      dynasty_value_score: 63.8,
      dvs_band_low: 30.1,
      dvs_band_high: 97.5,
      xvar: 4.2,
      xvar_percentile_position: 55.0,
      projection_1y: null,
      projection_2y: 12.0,
      projection_3y: null,
    });
    expect(fact("Dynasty value")).toBe("63.8");
    expect(fact("Scored by")).toBe("A blend of the rookie and active-player models");
    expect(within(lane()).queryByText(/likely range/i)).toBeNull();
    expect(within(lane()).queryByText(/30 to 98/)).toBeNull();
    expect(lane().querySelector("[data-basis]").getAttribute("data-basis")).toBe(
      "blend",
    );
  });

  it("prints no range fact for a number the API ships without a band either", () => {
    renderModel({
      engine_path: "ENGINE_B",
      dvs_engine: "B",
      model_grade: "ACTIVE_B",
      model_version: "engine_b_v2",
      dynasty_value_score: 71.0,
      dvs_band_low: null,
      dvs_band_high: null,
      xvar: null,
      xvar_percentile_position: null,
      projection_1y: null,
      projection_2y: null,
      projection_3y: null,
    });
    expect(within(lane()).getByText("Dynasty value")).toBeTruthy();
    expect(within(lane()).queryByText(/likely range/i)).toBeNull();
    expect(lane().querySelector("[data-basis]").getAttribute("data-basis")).toBe("B");
  });
});
