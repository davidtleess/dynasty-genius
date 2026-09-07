// @vitest-environment jsdom
import { cleanup, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, expect, it, vi } from "vitest";
import type { MarketRanksAvailable } from "../lib/api";
import { useAssetCatalogSearch } from "../trade/useAssetCatalogSearch";
import { MarketRanksContext } from "./MarketRanksContext";

// Search consumes only identity fields; full API validation happens at the provider.
const data = {
  rows: [
    { sleeper_id: "unowned", name: "Will Howard", position: "QB", on_roster: false },
    { sleeper_id: "owned", name: "Tucker Kraft", position: "TE", on_roster: true },
  ],
} as MarketRanksAvailable;
const wrapper = ({ children }: { children: ReactNode }) => (
  <MarketRanksContext.Provider value={{ status: "available", data }}>
    {children}
  </MarketRanksContext.Provider>
);
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
it("global player search reaches unowned rows and immediately follows the current query", () => {
  const f = vi.fn();
  vi.stubGlobal("fetch", f);
  const { result, rerender } = renderHook(({ q }) => useAssetCatalogSearch(q, true), {
    wrapper,
    initialProps: { q: "Will" },
  });
  expect(result.current.results.map((r) => r.sleeper_id)).toEqual(["unowned"]);
  rerender({ q: "Tucker" });
  expect(result.current.results.map((r) => r.sleeper_id)).toEqual(["owned"]);
  rerender({ q: "no match" });
  expect(result.current.results).toEqual([]);
  expect(f).not.toHaveBeenCalled();
});
it("trade asset search retains its existing catalog", async () => {
  const f = vi
    .fn()
    .mockResolvedValue({ ok: true, json: async () => ({ results: [] }) });
  vi.stubGlobal("fetch", f);
  renderHook(() => useAssetCatalogSearch("Will"), { wrapper });
  await waitFor(() =>
    expect(f).toHaveBeenCalledWith(
      "/api/trade/assets?q=Will&limit=50",
      expect.anything(),
    ),
  );
});
