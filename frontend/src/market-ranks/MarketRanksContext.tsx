import { createContext, type ReactNode, useContext, useEffect, useState } from "react";
import type { MarketRanksAvailable } from "../lib/api";
import { zMarketRanksApiResearchMarketRanksGetResponse } from "../lib/api/zod.gen";

export type RankState =
  | { status: "loading" | "error" | "not_configured" }
  | { status: "available"; data: MarketRanksAvailable };

// Bare legacy components stay usable; the actual application always mounts the provider.
export const MarketRanksContext = createContext<RankState>({
  status: "not_configured",
});
export const useMarketRanks = () => useContext(MarketRanksContext);

export function MarketRanksProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<RankState>({ status: "loading" });
  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const response = await fetch("/api/research/market-ranks");
        if (!response.ok) throw new Error("Comparison unavailable");
        const data = zMarketRanksApiResearchMarketRanksGetResponse.parse(
          await response.json(),
        );
        if (active)
          setState(
            data.status === "available"
              ? { status: "available", data }
              : { status: "not_configured" },
          );
      } catch {
        if (active) setState({ status: "error" });
      }
    })();
    return () => {
      active = false;
    };
  }, []);
  return (
    <MarketRanksContext.Provider value={state}>{children}</MarketRanksContext.Provider>
  );
}
