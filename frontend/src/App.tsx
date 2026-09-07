import { MarketRanksProvider } from "./market-ranks/MarketRanksContext";
import { AppShell } from "./shell/AppShell";

export function App() {
  return (
    <MarketRanksProvider>
      <AppShell />
    </MarketRanksProvider>
  );
}
