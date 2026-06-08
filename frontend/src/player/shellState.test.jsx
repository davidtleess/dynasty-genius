// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { zPlayerDetailResponse } from "../lib/api/zod.gen";
import { AppShell } from "../shell/AppShell";

function playerDetail() {
  return zPlayerDetailResponse.parse({
    caveats: [],
    decision_supported: false,
    degradation: null,
    divergence: { delta: -0.237, status: "model_lower_than_market" },
    evidence: {
      caveats: { caveats: [], items: ["Draft capital verified"] },
      counter_argument: {
        caveats: [],
        status: "available",
        text: "Premium valuation context.",
      },
      risk_flags: { caveats: [], items: [] },
      top_drivers: { caveats: [], items: ["age window"] },
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
      market_value: 4371,
      source: "fantasycalc",
      source_timestamp: "2026-05-24T17:19:52Z",
      status: "available",
    },
    model: {
      dynasty_value_score: 85.14,
      engine_path: "ENGINE_A",
      model_grade: "PROSPECT_D",
      model_version: "engine_a_v3",
      projection_1y: null,
      projection_2y: null,
      projection_3y: null,
      xvar: 10.31,
      xvar_percentile_position: 0.91,
    },
    model_status: "modeled",
    sleeper_id: "13269",
    source_timestamps: { market: "2026-05-24T17:19:52Z", pvo: "2026-06-07T14:32:45Z" },
  });
}

function mockAssetAndPlayerFetch() {
  globalThis.fetch = vi.fn((url) => {
    const href = String(url);
    if (href.startsWith("/api/trade/assets")) {
      return Promise.resolve({
        json: vi.fn().mockResolvedValue(catalogResponse()),
        ok: true,
        status: 200,
      });
    }
    if (href.startsWith("/api/players/")) {
      return Promise.resolve({
        json: vi.fn().mockResolvedValue(playerDetail()),
        ok: true,
        status: 200,
      });
    }
    throw new Error(`unexpected fetch ${href}`);
  });
}

function catalogEntry(overrides = {}) {
  return {
    asset_id: "player-13269",
    caveats: [],
    decision_supported: false,
    kind: "player",
    label: "Chase",
    market_ref: {
      asset_kind: "player",
      decision_supported: false,
      player_id: "13269",
      sleeper_id: "13269",
    },
    model_payload: {
      decision_supported: false,
      is_prospect: true,
      player_id: "13269",
      position: "QB",
      xvar: 10.31,
    },
    position: "QB",
    roster_owner_id: null,
    roster_owner_name: null,
    sleeper_id: "13269",
    ...overrides,
  };
}

function catalogResponse(results = [catalogEntry()]) {
  return {
    caveats: [],
    decision_supported: false,
    query: "cha",
    results,
    source_timestamp: "2026-06-07T21:20:00Z",
  };
}

function mockAssetFetch() {
  globalThis.fetch = vi.fn((url) => {
    const href = String(url);
    if (href.startsWith("/api/trade/assets")) {
      return Promise.resolve({
        json: vi.fn().mockResolvedValue(catalogResponse()),
        ok: true,
        status: 200,
      });
    }
    throw new Error(`unexpected fetch ${href}`);
  });
}

async function openTradeLabAndSelectAsset() {
  fireEvent.click(screen.getByRole("button", { name: "Trade Lab" }));
  fireEvent.change(screen.getByRole("searchbox", { name: "Search tradeable assets" }), {
    target: { value: "cha" },
  });
  fireEvent.click(await screen.findByRole("button", { name: "Chase" }));
}

function inspector() {
  return screen.getByRole("complementary", { name: "Player inspector" });
}

describe("Surface-3 shell player selection state", () => {
  beforeEach(() => {
    localStorage.clear();
    mockAssetFetch();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("opens the minimal player inspector when an AssetSearch result is selected", async () => {
    render(<AppShell />);

    await openTradeLabAndSelectAsset();

    await waitFor(() => {
      expect(inspector().dataset.state).toBe("open");
    });
    expect(within(inspector()).getByText("Chase")).toBeTruthy();
    expect(within(inspector()).getByText("13269")).toBeTruthy();
    expect(
      within(inspector()).getByRole("button", { name: "Open full evidence card" }),
    ).toBeTruthy();
    expect(within(inspector()).queryByText(/dynasty value score/i)).toBeNull();
    expect(within(inspector()).queryByText(/edge/i)).toBeNull();
  });

  it("lets a Trade Lab player chip reopen the inspector after close", async () => {
    render(<AppShell />);

    await openTradeLabAndSelectAsset();
    fireEvent.click(
      within(inspector()).getByRole("button", { name: "Close player inspector" }),
    );
    expect(inspector().dataset.state).toBe("closed");

    fireEvent.click(
      within(screen.getByRole("region", { name: /david sends/i })).getByRole("button", {
        name: "Chase",
      }),
    );

    expect(inspector().dataset.state).toBe("open");
    expect(within(inspector()).getByText("Chase")).toBeTruthy();
    expect(within(inspector()).getByText("13269")).toBeTruthy();
  });

  it("opens the full player detail page in main from the inspector action", async () => {
    mockAssetAndPlayerFetch();
    render(<AppShell />);

    await openTradeLabAndSelectAsset();
    fireEvent.click(
      within(inspector()).getByRole("button", { name: "Open full evidence card" }),
    );

    const card = await screen.findByRole("article", {
      name: /player detail for chase/i,
    });
    expect(
      within(screen.getByRole("main")).getByRole("article", {
        name: /player detail for chase/i,
      }),
    ).toBe(card);
    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith("/api/players/13269");
    });
  });
});
