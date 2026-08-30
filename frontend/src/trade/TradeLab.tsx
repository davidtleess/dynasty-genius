import { useState } from "react";
import type { ZodType, z } from "zod";

import {
  zTradeMarketReconciliation,
  zTradeRosterReconciliation,
} from "../lib/api/zod.gen";
import { AssetSearch } from "./AssetSearch";
import { LaneDegradedState } from "./LaneDegradedState";
import { MarketLanePanel } from "./MarketLanePanel";
import { ModelLanePanel } from "./ModelLanePanel";
import { RunComparisonBar } from "./RunComparisonBar";
import { TradeSideBuilder } from "./TradeSideBuilder";
import { TradeVerdict } from "./TradeVerdict";
import type { CatalogEntry, Side, Trade } from "./tradeState";
import { addAsset, loadTrade, removeAsset, saveTrade } from "./tradeState";
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

  // A priced result describes ONE board. The moment the board changes it stops
  // being true of what is on screen, so it is cleared rather than left standing.
  //
  // DG-116 panel finding, measured: this ticket wires up `removeAsset` (dead
  // since the surface shipped), which made a new state reachable — price a
  // trade, remove both sides, and the columns read "Nothing here yet." while
  // 2,900 characters of verdict and both lanes went on asserting the arithmetic
  // of a trade that was no longer there, with the empty-board guidance
  // suppressed because it is gated on `hasRun`. The honesty law's "stale must
  // still say it is stale" is satisfied here by not keeping the stale thing.
  function clearPricing(): void {
    setModelLane({ status: "idle" });
    setMarketLane({ status: "idle" });
  }

  function select(entry: CatalogEntry): void {
    setTrade((current) => {
      const next = addAsset(current, activeSide, entry);
      saveTrade(next);
      return next;
    });
    clearPricing();
    // Selecting an asset also opens the player inspector (entry-point wiring).
    onSelectPlayer?.(entry);
  }

  function drop(side: Side, assetId: string): void {
    setTrade((current) => {
      const next = removeAsset(current, side, assetId);
      saveTrade(next);
      return next;
    });
    clearPricing();
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
  const isEmptyBoard = trade.sent.length === 0 && trade.received.length === 0;

  return (
    <section className="dg-trade-lab" aria-label="Trade Lab">
      {/* The inc-3 mitigation contract (trade_lab_fe_mitigation_v1), always
          before the lane pair in DOM order.

          DG-111 — this paragraph was byte-locked and carried the standard
          disclosure line beneath it. David's 2026-08-29 ruling is the sign-off
          that replaces both, and the replacement is recorded verbatim in the
          ticket. Every fact survives: we do not compute a win/lose verdict, we
          do not judge fit, the two pricings stay separate rather than blended,
          a stale or missing price says so in its own lane, and the call is
          yours. Said the way you would say it at the table. */}
      <aside className="dg-caveat-note" role="note" aria-label="Trade Lab caveat">
        <p data-mitigation-contract>
          We price both sides two ways — what the dynasty market is paying, and what our
          model says — and keep the two apart instead of blending them into one number.
          Where a price is stale or missing, that lane says so. We don't call the winner
          and we don't judge whether the deal fits your team: that part is yours.
        </p>
      </aside>
      <div className="dg-trade-lab__builder">
        <AssetSearch
          onSelect={select}
          label="Add a player or a draft pick"
          placeholder="Start typing a name…"
          visibleLabel
          hint={
            activeSide === "sent"
              ? "Picking someone puts him on the side you send."
              : "Picking someone puts him on the side you get."
          }
        />
        <div className="dg-trade-lab__sides">
          <TradeSideBuilder
            side="sent"
            label="You send"
            entries={trade.sent}
            active={activeSide === "sent"}
            onActivate={setActiveSide}
            onRemove={drop}
            onSelectPlayer={onSelectPlayer}
          />
          <TradeSideBuilder
            side="received"
            label="You get"
            entries={trade.received}
            active={activeSide === "received"}
            onActivate={setActiveSide}
            onRemove={drop}
            onSelectPlayer={onSelectPlayer}
          />
        </div>
        <RunComparisonBar
          counterpartyRosterId={trade.counterpartyRosterId}
          onCounterpartyChange={setCounterparty}
          onRun={() => void run()}
        />
      </div>
      {/* What used to be here was roughly 700px of empty canvas. A first-time
          board now says what the surface does and how to work it. */}
      {!hasRun && isEmptyBoard && (
        <section className="dg-trade-lab__empty" aria-label="Build a trade">
          <h2 className="dg-trade-lab__empty-title">Build a trade</h2>
          <ol className="dg-trade-lab__empty-steps">
            <li>
              Choose a column — <strong>You send</strong> or <strong>You get</strong>.
            </li>
            <li>
              Search a player or a draft pick above and pick him; he lands on the column
              you chose.
            </li>
            <li>
              Press <strong>Price this trade</strong>.
            </li>
          </ol>
          <p className="dg-trade-lab__empty-note">
            You will get both sides priced two ways — what the dynasty market is paying
            for them, and what our own model makes of them — side by side, with the
            disagreement named where there is one.
          </p>
        </section>
      )}
      {hasRun && (
        <>
          {(modelData || marketData) && (
            <TradeVerdict model={modelData} market={marketData} />
          )}
          <div className="dg-trade-lab__lanes" data-testid="trade-lane-pair">
            {modelLane.status === "ready" && (
              <ModelLanePanel reconciliation={modelLane.data} />
            )}
            {modelLane.status === "unavailable" && (
              <LaneDegradedState label="Our model" />
            )}
            {marketLane.status === "ready" && (
              <MarketLanePanel reconciliation={marketLane.data} />
            )}
            {marketLane.status === "unavailable" && (
              <LaneDegradedState label="Market prices" />
            )}
          </div>
        </>
      )}
    </section>
  );
}
