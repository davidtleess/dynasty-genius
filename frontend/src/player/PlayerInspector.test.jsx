// @vitest-environment jsdom

import { render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { zPlayerDetailResponse } from "../lib/api/zod.gen";
import { PlayerInspector } from "./PlayerInspector";

function modeledDetail(overrides = {}) {
  return zPlayerDetailResponse.parse({
    caveats: [],
    decision_supported: false,
    degradation: null,
    divergence: {
      delta: 0.27,
      status: "model_higher_than_market",
    },
    evidence: {
      caveats: {
        caveats: [],
        items: [
          "Market snapshot stale",
          "Draft capital verified",
          "Projection source available",
        ],
      },
      counter_argument: {
        caveats: [],
        status: "available",
        text: "Premium valuation assumes high-level rushing or passing efficiency.",
      },
      risk_flags: {
        caveats: [],
        items: ["projection variance elevated"],
      },
      top_drivers: {
        caveats: [],
        items: ["age window", "draft capital"],
      },
    },
    identity: {
      age: 22,
      draft_class: 2026,
      name: "Chase",
      nfl_draft_pick: 1,
      nfl_draft_round: 1,
      position: "QB",
      sleeper_id: "13269",
      team: "LVR",
    },
    market: {
      caveats: ["market_overlay_static_caveat"],
      market_rank_overall: 42,
      market_rank_position: 8,
      market_value: 4100,
      source: "fantasycalc",
      source_timestamp: "2026-05-24T17:19:52Z",
      status: "available",
    },
    model: {
      dynasty_value_score: 85.14,
      engine_path: "ENGINE_A",
      model_grade: "PROSPECT_D",
      model_version: "fixture_model_v1",
      projection_1y: null,
      projection_2y: null,
      projection_3y: null,
      xvar: 10.31,
      xvar_percentile_position: null,
    },
    model_status: "modeled",
    sleeper_id: "13269",
    source_timestamps: {
      market: "2026-05-24T17:19:52Z",
      pvo: "2026-06-07T14:32:45Z",
    },
    ...overrides,
  });
}

function unmodeledDetail() {
  return modeledDetail({
    degradation: { message: "No active model score for this player category." },
    divergence: {
      delta: null,
      status: "unavailable",
    },
    evidence: null,
    market: {
      caveats: ["market_overlay_unavailable"],
      market_rank_overall: null,
      market_rank_position: null,
      market_value: null,
      source: null,
      source_timestamp: null,
      status: "unavailable",
    },
    model: null,
    model_status: "experimental",
  });
}

function partialDetail() {
  return modeledDetail({
    divergence: {
      delta: null,
      status: "unavailable",
    },
    evidence: {
      caveats: { caveats: [], items: [] },
      counter_argument: {
        caveats: ["counter_argument_unavailable"],
        status: "experimental",
        text: null,
      },
      risk_flags: { caveats: [], items: [] },
      top_drivers: { caveats: [], items: [] },
    },
    market: {
      caveats: ["market_overlay_unavailable"],
      market_rank_overall: null,
      market_rank_position: null,
      market_value: null,
      source: null,
      source_timestamp: null,
      status: "unavailable",
    },
  });
}

function mockPlayerDetail(detail) {
  globalThis.fetch = vi.fn().mockResolvedValue({
    json: vi.fn().mockResolvedValue(detail),
    ok: true,
    status: 200,
  });
}

function renderInspector(sleeperId = "13269") {
  render(
    <aside aria-label="Player inspector">
      <PlayerInspector player={{ label: "Chase", sleeperId }} onClose={vi.fn()} />
    </aside>,
  );
  return screen.getByRole("complementary", { name: "Player inspector" });
}

describe("PlayerInspector neutral preview", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches player detail and renders modeled status with presence counts only", async () => {
    mockPlayerDetail(modeledDetail());

    const inspector = renderInspector();

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith("/api/players/13269");
    });
    expect(await within(inspector).findByText("Modeled")).toBeTruthy();
    expect(within(inspector).getByText("Market available")).toBeTruthy();
    expect(
      within(inspector).getByText("3 caveats · counter-argument available"),
    ).toBeTruthy();
    expect(within(inspector).getByText("2 drivers · 1 risk flag")).toBeTruthy();
    expect(within(inspector).getByText("Decision support only")).toBeTruthy();
    expect(
      within(inspector).getByRole("button", { name: "Open full evidence card" }),
    ).toBeTruthy();

    expect(within(inspector).queryByText("PROSPECT_D")).toBeNull();
    expect(within(inspector).queryByText("85.14")).toBeNull();
    expect(within(inspector).queryByText("0.27")).toBeNull();
    expect(within(inspector).queryByText(/Premium valuation/i)).toBeNull();
    expect(within(inspector).queryByText(/Market snapshot stale/i)).toBeNull();
    expect(within(inspector).queryByText(/Tier/i)).toBeNull();
    expect(within(inspector).queryByText("⚠")).toBeNull();
    expect(within(inspector).queryByText(/recommended/i)).toBeNull();
  });

  it("labels unmodeled categories explicitly without generic evidence fallback text", async () => {
    mockPlayerDetail(unmodeledDetail());

    const inspector = renderInspector();

    expect(await within(inspector).findByText("Unmodeled category")).toBeTruthy();
    expect(within(inspector).getByText("No active model score")).toBeTruthy();
    expect(within(inspector).getByText("Market unavailable")).toBeTruthy();
    expect(within(inspector).queryByText(/evidence incomplete/i)).toBeNull();
    expect(within(inspector).queryByText(/dynasty value score/i)).toBeNull();
  });

  it("degrades partial detail into status and presence labels without fabricating data", async () => {
    mockPlayerDetail(partialDetail());

    const inspector = renderInspector();

    expect(await within(inspector).findByText("Modeled")).toBeTruthy();
    expect(within(inspector).getByText("Market unavailable")).toBeTruthy();
    expect(
      within(inspector).getByText("0 caveats · counter-argument unavailable"),
    ).toBeTruthy();
    expect(within(inspector).getByText("0 drivers · 0 risk flags")).toBeTruthy();
    expect(within(inspector).queryByText(/Premium valuation/i)).toBeNull();
    expect(within(inspector).queryByText(/projection variance/i)).toBeNull();
  });
});
