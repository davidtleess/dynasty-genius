// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AssetSearch } from "./AssetSearch";

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

function catalogResponse(overrides = {}) {
  return {
    caveats: ["future_picks_from_snapshot_not_live_sleeper"],
    decision_supported: false,
    query: "cha",
    results: [catalogEntry()],
    source_timestamp: "2026-05-24T17:19:44Z",
    ...overrides,
  };
}

function mockFetchResponse(body, init = {}) {
  const ok = init.ok ?? true;
  const status = init.status ?? (ok ? 200 : 500);

  globalThis.fetch = vi.fn().mockResolvedValue({
    json: vi.fn().mockResolvedValue(body),
    ok,
    status,
  });
}

describe("AssetSearch", () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders a searchbox and selects a validated catalog result", async () => {
    mockFetchResponse(catalogResponse());
    const onSelect = vi.fn();

    render(<AssetSearch onSelect={onSelect} />);
    fireEvent.change(screen.getByRole("searchbox"), {
      target: { value: "cha" },
    });

    await screen.findByText("Chase");
    fireEvent.click(screen.getByRole("button", { name: "Chase" }));

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith("/api/trade/assets?q=cha");
    });
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ asset_id: "100" }));
  });

  it("does not query for inputs shorter than 3 characters", async () => {
    const onSelect = vi.fn();

    render(<AssetSearch onSelect={onSelect} />);
    fireEvent.change(screen.getByRole("searchbox"), {
      target: { value: "ch" },
    });

    await waitFor(() => {
      expect(globalThis.fetch).not.toHaveBeenCalled();
    });
    expect(screen.queryByRole("button", { name: "Chase" })).toBeNull();
  });

  it("clears results without crashing when the catalog response is not ok", async () => {
    mockFetchResponse({ detail: "unavailable" }, { ok: false, status: 503 });

    render(<AssetSearch onSelect={vi.fn()} />);
    fireEvent.change(screen.getByRole("searchbox"), {
      target: { value: "cha" },
    });

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalled();
    });
    expect(screen.queryByRole("button", { name: "Chase" })).toBeNull();
  });

  it("clears results without crashing when Zod validation fails", async () => {
    mockFetchResponse({ query: "cha", results: [{ label: "Chase" }] });

    render(<AssetSearch onSelect={vi.fn()} />);
    fireEvent.change(screen.getByRole("searchbox"), {
      target: { value: "cha" },
    });

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalled();
    });
    expect(screen.queryByRole("button", { name: "Chase" })).toBeNull();
  });
});
