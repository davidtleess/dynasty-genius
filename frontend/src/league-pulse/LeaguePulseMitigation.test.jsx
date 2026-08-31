// @vitest-environment jsdom

import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TradePartners } from "../trade/TradePartners";
import { leaguePulseResponse } from "./fixtures";
import { LeaguePulse } from "./LeaguePulse";

const __dirname = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(__dirname, "../../..");
const postureSource = readFileSync(
  resolve(repoRoot, "src/dynasty_genius/team_posture.py"),
  "utf-8",
);
const cssSource = readFileSync(
  resolve(repoRoot, "frontend/src/league-pulse/LeaguePulse.css"),
  "utf-8",
);

// league_pulse_fe_mitigation_v1
//
// DG-111 — replacement copy. David's 2026-08-29 ruling is the sign-off that
// released the byte lock; the replacement is recorded verbatim in the ticket.
// Every fact the lock protected survives, in the same DOM position ahead of
// every panel: the labels are COMPUTED from four named roster signals, the
// weights are disclosed directly below, and a manager's real intent, private
// valuations and willingness to trade are explicitly beyond what we can see.
const MITIGATION_COPY =
  "We label each team contending, rebuilding and so on by reading four things off its roster — starter-weighted model value, roster age profile, early draft-pick balance, and taxi/development stash — weighted as shown below. That is our read of the roster, not a read of the manager: what they actually intend to do, how they really value their own players, and whether they want to trade at all are things nobody can see from here.";

const EXPECTED_WEIGHT_LABELS = {
  starter_weighted_model_value: "starter-weighted model value",
  roster_age_profile: "roster age profile",
  early_draft_pick_balance: "early draft-pick balance",
  taxi_development_stash: "taxi/development stash",
};

function mockFetch(body = leaguePulseResponse()) {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => body,
  });
}

function extractPostureSignalWeights() {
  const match = postureSource.match(/POSTURE_SIGNAL_WEIGHTS\s*=\s*{([\s\S]*?)}/m);
  expect(match, "team_posture.py must export POSTURE_SIGNAL_WEIGHTS").not.toBeNull();
  const body = match[1];
  return Object.fromEntries(
    Object.keys(EXPECTED_WEIGHT_LABELS).map((key) => {
      const valueMatch = body.match(new RegExp(`["']?${key}["']?\\s*:\\s*([0-9.]+)`));
      expect(valueMatch, `POSTURE_SIGNAL_WEIGHTS missing ${key}`).not.toBeNull();
      return [key, Number(valueMatch[1])];
    }),
  );
}

afterEach(() => vi.restoreAllMocks());

describe("League Pulse graduation mitigation", () => {
  it("renders exact no-intent-certainty copy above every League Pulse panel on initial load", async () => {
    mockFetch();

    render(<LeaguePulse />);

    const surface = await screen.findByTestId("league-pulse-ready");
    const mitigation = within(surface).getByText(MITIGATION_COPY);
    const mitigationBlock = mitigation.closest("[data-mitigation-contract]");

    expect(mitigationBlock).toBeTruthy();
    expect(mitigationBlock.getAttribute("data-mitigation-contract")).toBe(
      "league_pulse_fe_mitigation_v1",
    );

    for (const panel of [
      screen.getByRole("region", { name: /team postures/i }),
      screen.getByRole("region", { name: /team value overview/i }),
      screen.getByRole("region", { name: /model-native opportunity cards/i }),
      screen.getByRole("region", { name: /market overlay opportunity cards/i }),
    ]) {
      expect(
        mitigationBlock.compareDocumentPosition(panel) &
          Node.DOCUMENT_POSITION_FOLLOWING,
      ).toBeTruthy();
    }
  });

  // DG-114: the contract is "wherever posture words render", not "on League
  // Pulse". Partner Rankings prints perspective_posture and counterparty_posture
  // and now lives on Trades, so the same paragraph, carrying the same contract
  // marker, has to stand above it there.
  it("renders the same copy above the partner cards at their new address", async () => {
    mockFetch();

    render(<TradePartners />);

    const panel = await screen.findByRole("region", { name: /who to call/i });
    const mitigation = screen.getByText(MITIGATION_COPY);
    const mitigationBlock = mitigation.closest("[data-mitigation-contract]");

    expect(mitigationBlock.getAttribute("data-mitigation-contract")).toBe(
      "league_pulse_fe_mitigation_v1",
    );
    expect(
      mitigationBlock.compareDocumentPosition(panel) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it("couples the disclosed FE posture basis to the registered producer weights", async () => {
    const weights = extractPostureSignalWeights();
    mockFetch();

    render(<LeaguePulse />);

    const surface = await screen.findByTestId("league-pulse-ready");
    const basis = within(surface).getByTestId("league-pulse-posture-basis");

    for (const [key, label] of Object.entries(EXPECTED_WEIGHT_LABELS)) {
      const pct = `${Math.round(weights[key] * 100)}%`;
      expect(within(basis).getByText(new RegExp(label, "i"))).toBeTruthy();
      expect(within(basis).getByText(pct)).toBeTruthy();
    }
  });

  it("pins posture-neutral markers and source guards without banning legitimate posture enum words", async () => {
    mockFetch(
      leaguePulseResponse({
        team_postures: [
          {
            ...leaguePulseResponse().team_postures[0],
            roster_id: 1,
            posture_label: "CONTENDER",
          },
          {
            ...leaguePulseResponse().team_postures[0],
            roster_id: 2,
            team_name: "Team Two",
            posture_label: "REBUILDING",
          },
        ],
      }),
    );

    render(<LeaguePulse />);

    const surface = await screen.findByTestId("league-pulse-ready");
    const postureSection = within(surface).getByRole("region", {
      name: /team postures/i,
    });
    // DG-109: the posture enums still render as the neutral, marked labels
    // they always were — in a manager's words rather than in shouted caps.
    const contender = within(postureSection).getByText("Contending");
    const rebuilding = within(postureSection).getByText("Rebuilding");

    for (const label of [contender, rebuilding]) {
      const marker = label.closest("[data-posture-neutral]");
      expect(marker).toBeTruthy();
      expect(marker.getAttribute("data-posture-neutral")).toBe("true");
      expect(marker.hasAttribute("data-posture-dominance")).toBe(false);
    }

    const renderedTextWithoutDisclaimer = surface.textContent.replace(
      MITIGATION_COPY,
      "",
    );
    expect(renderedTextWithoutDisclaimer).not.toMatch(
      /\b(actual trade intent|active strategy|internal valuations|wants to trade|intends to trade|targeting strategy)\b/i,
    );

    const postureColorRule =
      /\.dg-league-pulse__[^{]*(posture|contender|rebuilding)[^{]*{[^}]*\b(color|background|border)\s*:/i;
    expect(cssSource).not.toMatch(postureColorRule);
    expect(cssSource).not.toMatch(
      /dg-league-pulse__[A-Za-z0-9_-]*(contender|rebuilding|posture-(green|red))/i,
    );
  });

  it("keeps market quarantine copy stable and styles mitigation text for narrow containers", async () => {
    mockFetch();

    render(<LeaguePulse />);

    const marketSection = await screen.findByRole("region", {
      name: /market overlay opportunity cards/i,
    });
    expect(
      within(marketSection).getByText(
        "Descriptive market signal, not a validated edge.",
      ),
    ).toBeTruthy();

    expect(cssSource).toMatch(/\.dg-league-pulse__mitigation\b/);
    expect(cssSource).toMatch(
      /\.dg-league-pulse__mitigation[\s\S]*\b(overflow-wrap|word-break)\s*:/,
    );

    await waitFor(() =>
      expect(globalThis.fetch).toHaveBeenCalledWith("/api/league/pulse"),
    );
  });
});
