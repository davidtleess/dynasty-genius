// @vitest-environment jsdom
//
// DG-128 (2026-09-01) — the band ships with the number on the player card too,
// and "Scored by" names what PRODUCED the score (the basis), not merely the lane
// the player is in.
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ValuationTwoLane } from "./ValuationTwoLane";

const market = { caveats: [], status: "unavailable" };
const divergence = { delta: null, status: "unavailable" };

function fact(label) {
  const lane = screen.getByTestId("player-model-lane");
  const dt = within(lane).getByText(label);
  return dt.nextElementSibling.textContent;
}

function renderModel(model) {
  render(<ValuationTwoLane model={model} market={market} divergence={divergence} />);
}

describe("the player card and the band", () => {
  it("prints the range beside a blended value and names the blend as its basis", () => {
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
    expect(fact("Likely range")).toBe("30 to 98");
    expect(fact("Scored by")).toBe("A blend of the rookie and active-player models");
    const lane = screen.getByTestId("player-model-lane");
    expect(lane.querySelector("[data-basis]").getAttribute("data-basis")).toBe("blend");
  });

  it("says the range is unknown when the number has none", () => {
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
    // The lane's own unknown marker, the same one every other absent fact shows.
    expect(fact("Likely range")).toBe("—");
  });
});
