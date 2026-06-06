// @vitest-environment jsdom

import { beforeEach, describe, expect, it } from "vitest";

import { addAsset, emptyTrade, loadTrade, removeAsset, saveTrade } from "./tradeState";

function catalogEntry(asset_id, label = asset_id) {
  return {
    asset_id,
    caveats: [],
    decision_supported: false,
    kind: asset_id.startsWith("pick:") ? "future_pick" : "player",
    label,
  };
}

describe("tradeState", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("starts with two empty sides and no selected counterparty", () => {
    expect(emptyTrade()).toEqual({
      counterpartyRosterId: null,
      received: [],
      sent: [],
    });
  });

  it("keeps duplicate picks distinct by asset_id", () => {
    let trade = emptyTrade();

    trade = addAsset(
      trade,
      "sent",
      catalogEntry("pick:2027:r1:orig5:owner1", "2027 1st via 5"),
    );
    trade = addAsset(
      trade,
      "sent",
      catalogEntry("pick:2027:r1:orig8:owner1", "2027 1st via 8"),
    );

    expect(trade.sent).toHaveLength(2);
    expect(trade.sent.map((entry) => entry.asset_id)).toEqual([
      "pick:2027:r1:orig5:owner1",
      "pick:2027:r1:orig8:owner1",
    ]);
  });

  it("removes by asset_id without collapsing the other side", () => {
    let trade = emptyTrade();
    trade = addAsset(trade, "received", catalogEntry("100", "Rostered Vet"));
    trade = addAsset(trade, "sent", catalogEntry("200", "Rostered Rookie"));

    trade = removeAsset(trade, "received", "100");

    expect(trade.received).toEqual([]);
    expect(trade.sent).toHaveLength(1);
    expect(trade.sent[0].asset_id).toBe("200");
  });

  it("round-trips through localStorage", () => {
    const trade = {
      ...emptyTrade(),
      counterpartyRosterId: 4,
      received: [catalogEntry("100", "Rostered Vet")],
      sent: [catalogEntry("pick:2027:r1:orig5:owner1", "2027 1st via 5")],
    };

    saveTrade(trade);

    expect(loadTrade()).toEqual(trade);
  });

  it("falls back to emptyTrade for empty or corrupt localStorage", () => {
    expect(loadTrade()).toEqual(emptyTrade());

    localStorage.setItem("dg.tradeLab.draft", "{not-json");

    expect(loadTrade()).toEqual(emptyTrade());
  });

  it("falls back to emptyTrade for valid JSON with the wrong shape", () => {
    // GREEN-side regression (Codex T3 review): valid JSON that is not a Trade
    // (null, missing/non-array sides) must not reach TradeLab and crash .map().
    localStorage.setItem("dg.tradeLab.draft", "null");
    expect(loadTrade()).toEqual(emptyTrade());

    localStorage.setItem("dg.tradeLab.draft", JSON.stringify({ sent: null }));
    expect(loadTrade()).toEqual(emptyTrade());
  });
});
