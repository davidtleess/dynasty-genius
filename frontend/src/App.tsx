import { MarketRanksProvider, useMarketRanks } from "./market-ranks/MarketRanksContext";
import { AppShell } from "./shell/AppShell";
import { Workspace } from "./workspace/Workspace";

function ProductSurface() {
  const ranks = useMarketRanks();
  const surface = new URLSearchParams(window.location.search).get("surface");
  const workspace =
    surface === null ||
    ["workspace", "roster", "roster-audit", "what-changed"].includes(surface);
  return workspace && ranks.status !== "not_configured" ? <Workspace /> : <AppShell />;
}

export function App() {
  return (
    <MarketRanksProvider>
      <ProductSurface />
    </MarketRanksProvider>
  );
}
