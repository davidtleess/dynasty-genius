import { useState } from "react";

import { AssetSearch } from "./AssetSearch";
import type { CatalogEntry, Trade } from "./tradeState";
import { addAsset, loadTrade, saveTrade } from "./tradeState";
import "./TradeLab.css";

// Surface-2 Trade Lab container. T3 wires the asset search + draft state;
// the two-side builder, parallel run, and the model/market lanes land in
// T4/T5. State is client-only (localStorage) — no server-side UI store.
export function TradeLab() {
  const [trade, setTrade] = useState<Trade>(() => loadTrade());

  function select(entry: CatalogEntry): void {
    setTrade((current) => {
      const next = addAsset(current, "sent", entry);
      saveTrade(next);
      return next;
    });
  }

  return (
    <section className="dg-trade-lab" aria-label="Trade Lab">
      <AssetSearch onSelect={select} />
      <ul className="dg-trade-lab__selected" aria-label="Selected assets">
        {trade.sent.map((entry) => (
          <li key={entry.asset_id}>{entry.label}</li>
        ))}
      </ul>
    </section>
  );
}
