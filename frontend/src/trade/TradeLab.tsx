import { useState } from "react";
import type { ZodType, z } from "zod";

import {
  zTradeMarketReconciliation,
  zTradeRosterReconciliation,
} from "../lib/api/zod.gen";
import { AssetSearch } from "./AssetSearch";
import { DivergenceStrip } from "./DivergenceStrip";
import { MarketLanePanel } from "./MarketLanePanel";
import { ModelLanePanel } from "./ModelLanePanel";
import { RunComparisonBar } from "./RunComparisonBar";
import { TradeSideBuilder } from "./TradeSideBuilder";
import type { CatalogEntry, Side, Trade } from "./tradeState";
import { addAsset, loadTrade, saveTrade } from "./tradeState";
import "./TradeLab.css";

// David's league context. The model and market lanes are kept physically
// separate: two distinct POSTs (model payloads -> /reconcile, market refs ->
// /reconcile/market) — never a single blended call or a combined delta.
const CURRENT_DRAFT_YEAR = 2026;
const FORMAT_KEY = "dynasty_sf_ppr";

type ModelReconciliation = z.infer<typeof zTradeRosterReconciliation>;
type MarketReconciliation = z.infer<typeof zTradeMarketReconciliation>;

// One lane: POST, then validate the 200 at the SDK boundary with the
// generated Zod schema. Not-ok or shape mismatch -> null (the lane degrades).
async function fetchLane<T>(
  url: string,
  body: unknown,
  schema: ZodType<T>,
): Promise<T | null> {
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      return null;
    }
    const parsed = schema.safeParse(await response.json());
    return parsed.success ? parsed.data : null;
  } catch {
    return null;
  }
}

export function TradeLab() {
  const [trade, setTrade] = useState<Trade>(() => loadTrade());
  const [activeSide, setActiveSide] = useState<Side>("sent");
  const [modelResult, setModelResult] = useState<ModelReconciliation | null>(null);
  const [marketResult, setMarketResult] = useState<MarketReconciliation | null>(null);

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

  async function run(): Promise<void> {
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
    const [model, market] = await Promise.all([
      fetchLane("/api/trade/reconcile", modelBody, zTradeRosterReconciliation),
      fetchLane("/api/trade/reconcile/market", marketBody, zTradeMarketReconciliation),
    ]);
    setModelResult(model);
    setMarketResult(market);
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
        onRun={() => void run()}
      />
      {(modelResult || marketResult) && (
        <>
          <div className="dg-trade-lab__lanes">
            {modelResult && <ModelLanePanel reconciliation={modelResult} />}
            {marketResult && <MarketLanePanel reconciliation={marketResult} />}
          </div>
          <DivergenceStrip model={modelResult} market={marketResult} />
        </>
      )}
    </section>
  );
}
