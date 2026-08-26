// @vitest-environment jsdom

import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
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
      // Pins the SR-15 contract: every request carries an abort signal so a
      // superseded query can never render over the current one.
      expect(globalThis.fetch).toHaveBeenCalledWith(
        "/api/trade/assets?q=cha",
        expect.objectContaining({ signal: expect.any(AbortSignal) }),
      );
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

// SR-15 / DG-080 — the stale-response race. Each request parses ~30 MB
// server-side, so completion order is scrambled: without an abort + debounce,
// whichever response resolves LAST wins the dropdown, and "brown" can render
// the results for "bro" (Brock Purdy offered as a match for "brown").
describe("AssetSearch stale-response and debounce guards", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  // Fetch stub with per-query latency. Honors the AbortController contract:
  // an aborted request rejects with AbortError and never resolves.
  function fetchWithLatency(routes) {
    return vi.fn((url, init) => {
      const q = new URL(url, "http://localhost").searchParams.get("q");
      const route = routes[q] ?? {
        body: catalogResponse({ query: q, results: [] }),
        delayMs: 5,
      };
      return new Promise((resolve, reject) => {
        const timer = setTimeout(() => {
          resolve({
            json: () => Promise.resolve(route.body),
            ok: true,
            status: 200,
          });
        }, route.delayMs);
        init?.signal?.addEventListener("abort", () => {
          clearTimeout(timer);
          reject(new DOMException("The operation was aborted.", "AbortError"));
        });
      });
    });
  }

  it("never renders results for a query that is no longer in the box", async () => {
    const staleResults = [
      catalogEntry({ asset_id: "200", label: "Brock Purdy" }),
      catalogEntry({ asset_id: "201", label: "A.J. Brown" }),
    ];
    globalThis.fetch = fetchWithLatency({
      bro: {
        body: catalogResponse({ query: "bro", results: staleResults }),
        delayMs: 400,
      },
      brow: {
        body: catalogResponse({ query: "brow", results: staleResults }),
        delayMs: 400,
      },
      brown: {
        body: catalogResponse({
          query: "brown",
          results: [catalogEntry({ asset_id: "201", label: "A.J. Brown" })],
        }),
        delayMs: 10,
      },
    });

    render(<AssetSearch onSelect={vi.fn()} />);
    const box = screen.getByRole("searchbox");
    fireEvent.change(box, { target: { value: "b" } });
    fireEvent.change(box, { target: { value: "br" } });
    fireEvent.change(box, { target: { value: "bro" } });
    // Let the slow q=bro request take flight (each act boundary is a React
    // flush point, so the fetch effect actually issues its request)...
    await act(async () => {
      await vi.advanceTimersByTimeAsync(250);
    });
    // ...then finish typing while it is still pending...
    fireEvent.change(box, { target: { value: "brow" } });
    fireEvent.change(box, { target: { value: "brown" } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(250);
    });
    // ...and let every response timer settle. q=bro resolves LAST by design.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });

    expect(screen.getByRole("button", { name: "A.J. Brown" })).toBeTruthy();
    expect(screen.queryByText("Brock Purdy")).toBeNull();
  });

  it("debounces typing into exactly one request, for the final query", async () => {
    globalThis.fetch = fetchWithLatency({
      brown: {
        body: catalogResponse({
          query: "brown",
          results: [catalogEntry({ asset_id: "201", label: "A.J. Brown" })],
        }),
        delayMs: 10,
      },
    });

    render(<AssetSearch onSelect={vi.fn()} />);
    const box = screen.getByRole("searchbox");
    for (const value of ["b", "br", "bro", "brow", "brown"]) {
      fireEvent.change(box, { target: { value } });
    }
    // First advance fires the debounce (one fetch); second lets the response
    // timer resolve after the act boundary has flushed the fetch effect.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(250);
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(750);
    });

    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
    expect(globalThis.fetch.mock.calls[0][0]).toBe("/api/trade/assets?q=brown");
    expect(screen.getByRole("button", { name: "A.J. Brown" })).toBeTruthy();
  });
});
