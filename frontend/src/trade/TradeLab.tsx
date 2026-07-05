import { useState } from "react";
import type { ZodType, z } from "zod";

import {
  zTradeMarketReconciliation,
  zTradeRosterReconciliation,
} from "../lib/api/zod.gen";
import { AssetSearch } from "./AssetSearch";
import { DivergenceStrip } from "./DivergenceStrip";
import { LaneDegradedState } from "./LaneDegradedState";
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

// A lane is idle (not run), ready (200 + valid), or unavailable (not-ok or a
// 200 that failed schema validation). Coupled degradation is a backend fact:
// missing model artifacts 503 BOTH routes, so both lanes land "unavailable".
type LaneState<T> =
  | { status: "idle" }
  | { status: "ready"; data: T }
  | { status: "unavailable" };

async function fetchLane<T>(
  url: string,
  body: unknown,
  schema: ZodType<T>,
): Promise<LaneState<T>> {
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      return { status: "unavailable" };
    }
    const parsed = schema.safeParse(await response.json());
    return parsed.success
      ? { status: "ready", data: parsed.data }
      : { status: "unavailable" };
  } catch {
    return { status: "unavailable" };
  }
}

export function TradeLab({
  onSelectPlayer,
}: {
  onSelectPlayer?: ((entry: CatalogEntry) => void) | undefined;
} = {}) {
  const [trade, setTrade] = useState<Trade>(() => loadTrade());
  const [activeSide, setActiveSide] = useState<Side>("sent");
  const [modelLane, setModelLane] = useState<LaneState<ModelReconciliation>>({
    status: "idle",
  });
  const [marketLane, setMarketLane] = useState<LaneState<MarketReconciliation>>({
    status: "idle",
  });

  function select(entry: CatalogEntry): void {
    setTrade((current) => {
      const next = addAsset(current, activeSide, entry);
      saveTrade(next);
      return next;
    });
    // Selecting an asset also opens the player inspector (entry-point wiring).
    onSelectPlayer?.(entry);
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
    setModelLane(model);
    setMarketLane(market);
  }

  const modelData = modelLane.status === "ready" ? modelLane.data : null;
  const marketData = marketLane.status === "ready" ? marketLane.data : null;
  const hasRun = modelLane.status !== "idle" || marketLane.status !== "idle";

  return (
    <section className="dg-trade-lab" aria-label="Trade Lab">
      {/* H1 §1d: ONE standard region caveat block. The inner paragraph is the
          binding inc-3 mitigation contract (trade_lab_fe_mitigation_v1) —
          exact, non-state-claiming copy, byte-untouched, always before the
          lane pair in DOM order. Only its container changed. */}
      <aside className="dg-caveat-note" role="note" aria-label="Trade Lab caveat">
        <p data-mitigation-contract>
          This diagnostic panel does not calculate whether you win or lose this trade,
          and it does not judge if this transaction fits your team. It keeps the model
          and market views separate and surfaces stale or unavailable data as caveats,
          so you can evaluate the numbers yourself.
        </p>
        <p className="dg-caveat-note__disclosure">
          Descriptive only — not decision-grade.
        </p>
      </aside>
      <AssetSearch onSelect={select} />
      <div className="dg-trade-lab__sides">
        <TradeSideBuilder
          side="sent"
          label="David sends"
          entries={trade.sent}
          active={activeSide === "sent"}
          onActivate={setActiveSide}
          onSelectPlayer={onSelectPlayer}
        />
        <TradeSideBuilder
          side="received"
          label="David receives"
          entries={trade.received}
          active={activeSide === "received"}
          onActivate={setActiveSide}
          onSelectPlayer={onSelectPlayer}
        />
      </div>
      <RunComparisonBar
        counterpartyRosterId={trade.counterpartyRosterId}
        onCounterpartyChange={setCounterparty}
        onRun={() => void run()}
      />
      {hasRun && (
        <>
          <div className="dg-trade-lab__lanes" data-testid="trade-lane-pair">
            {modelLane.status === "ready" && (
              <ModelLanePanel reconciliation={modelLane.data} />
            )}
            {modelLane.status === "unavailable" && (
              <LaneDegradedState label="Model lane" />
            )}
            {marketLane.status === "ready" && (
              <MarketLanePanel reconciliation={marketLane.data} />
            )}
            {marketLane.status === "unavailable" && (
              <LaneDegradedState label="Market lane" />
            )}
          </div>
          {(modelData || marketData) && (
            <DivergenceStrip model={modelData} market={marketData} />
          )}
        </>
      )}
    </section>
  );
}
