// @vitest-environment jsdom
//
// DG-114 REVIEW FIX — the disclosures a moved panel takes with it.
//
// The first cut of this ticket moved Partner Rankings from League Pulse to
// Trades and carried only the posture disclosure. Three producer-emitted facts
// stayed behind on a header that no longer sits above the cards:
//
//   · `captured_at` — how old this snapshot is;
//   · `caveats: ["league_pulse_artifact_state_<date>"]` — emitted on EVERY
//     response (league_pulse_assembler.py:306-348), never absent;
//   · `dropped.partner_rankings` — partner records the assembler could not
//     match, incremented at :273-280 for THIS panel and no other.
//
// The browser proof could not see the gap because the live payload that day was
// same-day fresh with zero drops. These checks run the day it is not: a snapshot
// ten days old, with partners missing from the list.
//
// The honesty law: stale must still say it is stale, and a list with records
// withheld must not read as a complete list.

import { render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { leaguePulseResponse } from "../league-pulse/fixtures";
import { LeaguePulse } from "../league-pulse/LeaguePulse";
import { TradePartners } from "./TradePartners";

const STALE_CAPTURE = "2026-08-20T18:00:00Z";

function staleSnapshot(overrides = {}) {
  const base = leaguePulseResponse();
  return leaguePulseResponse({
    captured_at: STALE_CAPTURE,
    caveats: ["league_pulse_artifact_state_2026-08-20"],
    dropped: { ...base.dropped, partner_rankings: 2 },
    ...overrides,
  });
}

function mockFetch(body) {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => body,
  });
}

afterEach(() => vi.restoreAllMocks());

describe("Trade partners · the facts that travel with the panel", () => {
  it("says how old the snapshot is, above the cards priced from it", async () => {
    mockFetch(staleSnapshot());

    render(<TradePartners />);

    const asOf = await screen.findByText("as of Aug 20, 2026, 2:00 PM EDT");
    // The raw timestamp stays on the element: the sentence is a translation of
    // the receipt, never a replacement for it.
    expect(asOf.getAttribute("title")).toBe(STALE_CAPTURE);

    const artifactState = screen.getByText(
      "This league snapshot was built from data captured 2026-08-20.",
    );
    expect(artifactState.getAttribute("title")).toBe(
      "league_pulse_artifact_state_2026-08-20",
    );

    // Above the cards, not somewhere below them.
    const panel = screen.getByRole("region", { name: /partner rankings/i });
    expect(
      asOf.compareDocumentPosition(panel) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it("counts the partner records that could not be matched", async () => {
    mockFetch(staleSnapshot());

    render(<TradePartners />);

    expect(
      await screen.findByText(
        "2 partner records could not be matched up and are not shown below.",
      ),
    ).toBeTruthy();
  });

  it("does not print a withheld line when nothing was dropped", async () => {
    mockFetch(leaguePulseResponse());

    render(<TradePartners />);

    await screen.findByRole("region", { name: /partner rankings/i });
    expect(screen.queryByText(/could not be matched up/i)).toBeNull();
  });

  it("separates an empty list from a list whose records were all withheld", async () => {
    // The DG-110 defect in its worst form: every partner dropped. Without the
    // count, "No partner ranking context available." reads as "you have no good
    // trade partners" — an absence asserted where only a failure happened.
    mockFetch(
      staleSnapshot({
        partner_rankings: [],
        dropped: {
          ...leaguePulseResponse().dropped,
          partner_rankings: 11,
        },
      }),
    );

    render(<TradePartners />);

    expect(
      await screen.findByText(
        "11 partner records could not be matched up and are not shown below.",
      ),
    ).toBeTruthy();
    expect(screen.getByText("No partner ranking context available.")).toBeTruthy();
  });

  it("cites the artifact these cards were actually built from", async () => {
    mockFetch(staleSnapshot());

    render(<TradePartners />);

    // partner_rankings is read out of the league_opportunity artifact and no
    // other (league_pulse_assembler.py:272-280), so that is the one receipt
    // this page is entitled to print.
    const receipt = await screen.findByText(
      "League opportunity data: league_opportunity.v2",
    );
    expect(receipt.closest("ul")).toHaveProperty("dataset.receipt");
    expect(screen.queryByText(/Team posture data:/)).toBeNull();
  });
});

describe("Trade partners · a read that failed says which way it failed", () => {
  it("says the snapshot could not be loaded when no response arrives", async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new TypeError("network down"));

    render(<TradePartners />);

    // The single catch this replaced printed "The response was not in the
    // expected shape." for a request that never got a response at all.
    expect(
      await screen.findByText(
        "Trade partners unavailable. The league snapshot could not be loaded right now.",
      ),
    ).toBeTruthy();
  });

  it("keeps the shape sentence for a response it could not read", async () => {
    mockFetch({ not: "a league pulse response" });

    render(<TradePartners />);

    expect(
      await screen.findByText(
        "Could not read the league snapshot. The response was not in the expected shape.",
      ),
    ).toBeTruthy();
  });
});

describe("League Pulse · the withheld count follows its panel", () => {
  it("does not count partner drops on a page whose partner panel has left", async () => {
    const base = leaguePulseResponse();
    mockFetch(
      leaguePulseResponse({
        dropped: { ...base.dropped, partner_rankings: 3, team_values: 2 },
      }),
    );

    render(<LeaguePulse />);

    // The header's sentence ends "are not shown below". Since DG-114 the
    // partner panel is not below it, so counting its drops here would attach a
    // number to content this page does not carry — 5 where the page is missing
    // 2. The three partner drops are disclosed on Trades, against the panel
    // they belong to.
    await waitFor(() =>
      expect(
        screen.getByText("2 records could not be matched up and are not shown below."),
      ).toBeTruthy(),
    );
  });

  it("no longer promises a section it does not contain", async () => {
    mockFetch(leaguePulseResponse());

    render(<LeaguePulse />);

    const banner = await screen.findByRole("region", { name: /league pulse status/i });
    // "…who's contending, who's rebuilding, and who to call." survived the move
    // of the panel that answered the third clause. It does not survive here.
    expect(within(banner).queryByText(/who to call/i)).toBeNull();
    expect(within(banner).getByText(/read-only snapshot/i)).toBeTruthy();
    expect(within(banner).getByText(/we don't read minds/i)).toBeTruthy();
  });
});
