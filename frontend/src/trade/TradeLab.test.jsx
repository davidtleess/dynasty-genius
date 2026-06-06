// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TradeLab } from "./TradeLab";

function catalogEntry(overrides = {}) {
  return {
    asset_id: "100",
    caveats: [],
    decision_supported: false,
    kind: "player",
    label: "Chase",
    market_ref: {
      asset_kind: "player",
      decision_supported: false,
      player_id: "100",
      sleeper_id: "100",
    },
    model_payload: {
      decision_supported: false,
      is_prospect: false,
      player_id: "100",
      position: "WR",
      xvar: 22.5,
    },
    position: "WR",
    roster_owner_id: 1,
    roster_owner_name: "Woodbury Riders",
    ...overrides,
  };
}

function catalogResponse(results = [catalogEntry()]) {
  return {
    caveats: ["future_picks_from_snapshot_not_live_sleeper"],
    decision_supported: false,
    query: "cha",
    results,
    source_timestamp: "2026-05-24T17:19:44Z",
  };
}

function okJson(body) {
  return Promise.resolve({
    json: vi.fn().mockResolvedValue(body),
    ok: true,
    status: 200,
  });
}

function failedJson(body = { detail: "unavailable" }) {
  return Promise.resolve({
    json: vi.fn().mockResolvedValue(body),
    ok: false,
    status: 503,
  });
}

function installTradeLabFetch({ failModel = false, failMarket = false } = {}) {
  const calls = [];
  globalThis.fetch = vi.fn((url, init = {}) => {
    const href = String(url);
    const method = init.method ?? "GET";
    const parsedBody = init.body ? JSON.parse(init.body) : undefined;
    calls.push({ body: parsedBody, method, url: href });

    if (href.startsWith("/api/trade/assets")) {
      return okJson(catalogResponse());
    }
    if (href.endsWith("/api/trade/reconcile/market")) {
      return failMarket
        ? failedJson()
        : okJson({ caveats: [], decision_supported: false });
    }
    if (href.endsWith("/api/trade/reconcile")) {
      return failModel
        ? failedJson()
        : okJson({ caveats: [], decision_supported: false });
    }
    throw new Error(`unexpected fetch ${href}`);
  });
  return calls;
}

async function selectSearchResult(label = "Chase") {
  fireEvent.change(screen.getByRole("searchbox"), {
    target: { value: label.slice(0, 3).toLowerCase() },
  });
  fireEvent.click(await screen.findByRole("button", { name: label }));
}

function runButton() {
  return screen.getByRole("button", { name: /run comparison/i });
}

function sentRegion() {
  return screen.getByRole("region", { name: /david sends/i });
}

function receivedRegion() {
  return screen.getByRole("region", { name: /david receives/i });
}

describe("TradeLab two-side builder and parallel run", () => {
  beforeEach(() => {
    localStorage.clear();
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("adds a searched asset to the default sent side and runs both lanes with shaped payloads", async () => {
    const calls = installTradeLabFetch();

    render(<TradeLab />);
    await selectSearchResult();

    expect(within(sentRegion()).getByText("Chase")).toBeTruthy();
    expect(within(receivedRegion()).queryByText("Chase")).toBeNull();

    fireEvent.click(runButton());

    await waitFor(() => {
      expect(calls.some((call) => call.url.endsWith("/api/trade/reconcile"))).toBe(
        true,
      );
      expect(
        calls.some((call) => call.url.endsWith("/api/trade/reconcile/market")),
      ).toBe(true);
    });

    const model = calls.find((call) => call.url.endsWith("/api/trade/reconcile"));
    const market = calls.find((call) =>
      call.url.endsWith("/api/trade/reconcile/market"),
    );

    expect(model.method).toBe("POST");
    expect(model.body.david_assets[0]).toMatchObject({
      is_prospect: false,
      player_id: "100",
    });
    expect(model.body.received_assets).toEqual([]);
    expect(market.method).toBe("POST");
    expect(market.body.sent_assets[0]).toMatchObject({
      asset_kind: "player",
      sleeper_id: "100",
    });
    expect(market.body.received_assets).toEqual([]);
    expect(market.body).toMatchObject({
      current_draft_year: 2026,
      format_key: "dynasty_sf_ppr",
    });
    expect(market.body).not.toHaveProperty("counterparty_roster_id");
  });

  it("routes the next selected asset to received after switching active side", async () => {
    installTradeLabFetch();

    render(<TradeLab />);
    fireEvent.click(screen.getByRole("button", { name: /david receives/i }));
    await selectSearchResult();

    expect(within(receivedRegion()).getByText("Chase")).toBeTruthy();
    expect(within(sentRegion()).queryByText("Chase")).toBeNull();
  });

  it("includes counterparty_roster_id only when the selector is set", async () => {
    const calls = installTradeLabFetch();

    render(<TradeLab />);
    await selectSearchResult();
    fireEvent.change(screen.getByLabelText(/counterparty roster/i), {
      target: { value: "4" },
    });
    fireEvent.click(runButton());

    await waitFor(() => {
      expect(
        calls.some((call) => call.url.endsWith("/api/trade/reconcile/market")),
      ).toBe(true);
    });

    const market = calls.find((call) =>
      call.url.endsWith("/api/trade/reconcile/market"),
    );
    expect(market.body.counterparty_roster_id).toBe(4);
  });

  it("runs with empty sides and does not crash when one lane is unavailable", async () => {
    const calls = installTradeLabFetch({ failMarket: true });

    render(<TradeLab />);
    fireEvent.click(runButton());

    await waitFor(() => {
      expect(calls.some((call) => call.url.endsWith("/api/trade/reconcile"))).toBe(
        true,
      );
      expect(
        calls.some((call) => call.url.endsWith("/api/trade/reconcile/market")),
      ).toBe(true);
    });
  });
});
