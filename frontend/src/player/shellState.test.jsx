// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AppShell } from "../shell/AppShell";

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
});
