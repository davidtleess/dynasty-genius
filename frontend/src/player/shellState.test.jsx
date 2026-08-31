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
    frozen_prediction: {
      basis: "model_supported_prediction_captured",
      coverage: {
        current_rostered_skill_in_frozen_prediction_cohort_count: 221,
        current_rostered_skill_not_in_frozen_prediction_cohort_count: 53,
        current_rostered_skill_player_count: 274,
      },
      decision_supported: false,
      frozen_capture_date: "2026-08-05",
      message: "A model prediction was frozen for 2026 outcome evaluation.",
      season: 2026,
      status: "included",
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
  fireEvent.click(screen.getByRole("button", { name: "Trades" }));
  fireEvent.change(
    screen.getByRole("searchbox", { name: "Add a player or a draft pick" }),
    {
      target: { value: "cha" },
    },
  );
  fireEvent.click(await screen.findByRole("button", { name: "Chase" }));
}

function playerCard() {
  return screen.getByRole("dialog", { name: "Player card" });
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

  it("opens the player's card when an AssetSearch result is selected", async () => {
    mockAssetAndPlayerFetch();
    render(<AppShell />);

    await openTradeLabAndSelectAsset();

    const card = await screen.findByRole("dialog", { name: "Player card" });
    expect(
      await within(card).findByRole("article", { name: /player detail for chase/i }),
    ).toBeTruthy();
    // DG-109: the Sleeper id is a lookup key, not information about the
    // player — it stays on screen, labelled, in the receipt layer. DG-114
    // retired the preview it used to live on; the fact moved to the card.
    // DG-120 split the line into our label and the id itself, so the id can be
    // declared an identifier. The rendered line is byte-identical.
    expect(
      [...card.querySelectorAll("p")].some(
        (node) => node.textContent === "Sleeper id: 13269",
      ),
    ).toBe(true);
    // DG-114: the press asked for the card, so the card is what opens. There is
    // no second button to reach it.
    expect(
      within(card).queryByRole("button", { name: "Open full evidence card" }),
    ).toBeNull();
  });

  it("lets a Trade Lab player chip reopen the card after it is closed", async () => {
    mockAssetAndPlayerFetch();
    render(<AppShell />);

    await openTradeLabAndSelectAsset();
    fireEvent.click(
      within(playerCard()).getByRole("button", { name: "Close player card" }),
    );
    await waitFor(() =>
      expect(screen.queryByRole("dialog", { name: "Player card" })).toBeNull(),
    );

    fireEvent.click(
      within(screen.getByRole("region", { name: /you send/i })).getByRole("button", {
        name: "Chase",
      }),
    );

    const card = await screen.findByRole("dialog", { name: "Player card" });
    expect(
      await within(card).findByRole("article", { name: /player detail for chase/i }),
    ).toBeTruthy();
  });

  it("opens the card OVER the surface instead of replacing it", async () => {
    mockAssetAndPlayerFetch();
    render(<AppShell />);

    await openTradeLabAndSelectAsset();
    await screen.findByRole("dialog", { name: "Player card" });

    // The retired behaviour: the full card took over the main column, so the
    // trade you were building disappeared behind the player you were checking.
    // It is still there, and closing the card puts you back on it.
    expect(
      within(screen.getByRole("main")).queryByRole("article", {
        name: /player detail for chase/i,
      }),
    ).toBeNull();
    expect(screen.getByRole("region", { name: /you send/i })).toBeTruthy();
    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith("/api/players/13269");
    });
  });
});
