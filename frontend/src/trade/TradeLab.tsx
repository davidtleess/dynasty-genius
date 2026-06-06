import { useState } from "react";

import { AssetSearch } from "./AssetSearch";
import { RunComparisonBar } from "./RunComparisonBar";
import { TradeSideBuilder } from "./TradeSideBuilder";
import type { CatalogEntry, Side, Trade } from "./tradeState";
import { addAsset, loadTrade, saveTrade } from "./tradeState";
import "./TradeLab.css";

// David's league context. The model and market lanes are kept physically
// separate: two distinct POSTs (model payloads -> /reconcile, market refs ->
// /reconcile/market) — never a single blended call.
const CURRENT_DRAFT_YEAR = 2026;
const FORMAT_KEY = "dynasty_sf_ppr";

function postJson(url: string, body: unknown): Promise<unknown> {
  return fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).catch(() => undefined);
}

export function TradeLab() {
  const [trade, setTrade] = useState<Trade>(() => loadTrade());
  const [activeSide, setActiveSide] = useState<Side>("sent");

  function select(entry: CatalogEntry): void {
    setTrade((current) => {
      const next = addAsset(current, activeSide, entry);
      saveTrade(next);
      return next;
    });
  }

  function setCounterparty(value: number | null): void {
    setTrade((current) => {
      const next = { ...current, counterpartyRosterId: value };
      saveTrade(next);
      return next;
    });
  }

  function run(): void {
    const modelBody = {
      david_assets: trade.sent.map((entry) => entry.model_payload),
      received_assets: trade.received.map((entry) => entry.model_payload),
    };
    const marketBody: Record<string, unknown> = {
      sent_assets: trade.sent.map((entry) => entry.market_ref),
      received_assets: trade.received.map((entry) => entry.market_ref),
      current_draft_year: CURRENT_DRAFT_YEAR,
      format_key: FORMAT_KEY,
    };
    if (trade.counterpartyRosterId !== null) {
      marketBody.counterparty_roster_id = trade.counterpartyRosterId;
    }
    void Promise.all([
      postJson("/api/trade/reconcile", modelBody),
      postJson("/api/trade/reconcile/market", marketBody),
    ]);
  }

  return (
    <section className="dg-trade-lab" aria-label="Trade Lab">
      <AssetSearch onSelect={select} />
      <div className="dg-trade-lab__sides">
        <TradeSideBuilder
          side="sent"
          label="David sends"
          entries={trade.sent}
          active={activeSide === "sent"}
          onActivate={setActiveSide}
        />
        <TradeSideBuilder
          side="received"
          label="David receives"
          entries={trade.received}
          active={activeSide === "received"}
          onActivate={setActiveSide}
        />
      </div>
      <RunComparisonBar
        counterpartyRosterId={trade.counterpartyRosterId}
        onCounterpartyChange={setCounterparty}
        onRun={run}
      />
    </section>
  );
}
