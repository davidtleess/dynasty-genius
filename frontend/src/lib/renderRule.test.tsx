// @vitest-environment jsdom
//
// DG-109 — the enforcement test. This is the deliverable as much as the strings
// are: it mounts the real surfaces against REAL captured payloads and fails if
// any component prints a raw pipeline key. A future component that renders
// `evidence.caveats` straight, or adds a `<dt>{key}</dt>`, breaks this test.
//
// The fixtures in ./__fixtures__ were captured read-only from the live product
// (http://127.0.0.1:8000) on 2026-08-30 and trimmed only by shortening row
// arrays — no string was edited, so every token the audit sees is a token David
// can see. Capture commands are recorded in the DG-109 close-out.
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LeaguePulse } from "../league-pulse/LeaguePulse";
import { PlayerDetailCard } from "../player/PlayerDetailCard";
import { PlayerInspector } from "../player/PlayerInspector";
import { SystemHealthCard } from "../system-health/SystemHealthCard";
import { DailyTape } from "../ui/DailyTape";
import { DailyWhatChanged } from "../what-changed/DailyWhatChanged";
import leaguePulseLive from "./__fixtures__/leaguePulse.live.json";
import playerDetailLive from "./__fixtures__/playerDetail.live.json";
import systemHealthLive from "./__fixtures__/systemHealth.live.json";
import whatChangedLive from "./__fixtures__/whatChanged.live.json";
import { auditRenderedCopy, findRawCopy, formatRawCopyFindings } from "./renderRule";

// biome-ignore lint/suspicious/noExplicitAny: fixtures are captured wire payloads; the components' own Zod parse is the contract check under test.
type Wire = any;

function mockRoutes(routes: Record<string, unknown>) {
  globalThis.fetch = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    const body = routes[url];
    if (body === undefined) {
      return { ok: false, status: 503, json: async () => ({}) } as Response;
    }
    return { ok: true, status: 200, json: async () => body } as unknown as Response;
  }) as typeof fetch;
}

function expectClean(root: Element, surface: string) {
  const findings = auditRenderedCopy(root);
  expect(
    findings,
    `${surface} leaked raw pipeline keys to the screen:\n${formatRawCopyFindings(findings)}`,
  ).toEqual([]);
}

afterEach(() => vi.restoreAllMocks());

describe("the render rule: no raw pipeline key reaches the DOM", () => {
  it("flags underscore keys and shouted tokens, and leaves plain prose alone", () => {
    expect(findRawCopy("age_not_near_position_cliff")).toEqual([
      "age_not_near_position_cliff",
    ]);
    expect(findRawCopy("Signal completeness 83% — missing: ppg_t_minus_1")).toEqual([
      "ppg_t_minus_1",
    ]);
    expect(findRawCopy("REBUILDING")).toEqual(["REBUILDING"]);
    // One offender, one line to fix — not ENGINE_B plus its shouted halves.
    expect(findRawCopy("ENGINE_B")).toEqual(["ENGINE_B"]);
    // Fantasy vocabulary a manager reads as English survives untouched.
    expect(findRawCopy("QB · Giants · 22 years old")).toEqual([]);
    expect(
      findRawCopy("Age is on his side — years from the usual QB decline."),
    ).toEqual([]);
  });

  it("exempts the receipt layer and the league's own words, and nothing else", () => {
    const host = document.createElement("div");
    host.innerHTML = `
      <p>engine_b_not_decision_grade</p>
      <p data-receipt>artifact pvo_refresh</p>
      <h4 data-user-text>MDEF</h4>
      <span data-receipt><em>nested_raw_key</em></span>
    `;
    const findings = auditRenderedCopy(host);
    expect(findings.map((f) => f.token)).toEqual(["engine_b_not_decision_grade"]);
  });

  it("holds on the front page (Daily What-Changed) with live data", async () => {
    mockRoutes({ "/api/league/what-changed": whatChangedLive as Wire });

    const { container } = render(<DailyWhatChanged />);
    await screen.findByRole("region", { name: /daily what-changed/i });

    expectClean(container, "Daily What-Changed");
  });

  it("holds on the player card with live data", () => {
    const { container } = render(
      <PlayerDetailCard detail={playerDetailLive as Wire} />,
    );
    expectClean(container, "player card");
  });

  it("holds on the player inspector with live data", async () => {
    mockRoutes({ "/api/players/12508": playerDetailLive as Wire });

    const { container } = render(
      <PlayerInspector
        player={{ sleeperId: "12508", label: "Jaxson Dart" }}
        onClose={() => {}}
      />,
    );
    await waitFor(() => expect(screen.queryByText(/loading/i)).toBeNull());

    expectClean(container, "player inspector");
  });

  it("holds on the league surfaces with live data", async () => {
    mockRoutes({ "/api/league/pulse": leaguePulseLive as Wire });

    const { container } = render(<LeaguePulse />);
    await screen.findByTestId("league-pulse-ready");

    expectClean(container, "League Pulse");
  });

  it("holds on the data-freshness card with live data", async () => {
    mockRoutes({ "/api/health": systemHealthLive as Wire });

    const { container } = render(<SystemHealthCard now={new Date("2026-08-30")} />);
    await screen.findByText(/data freshness/i);

    expectClean(container, "System health card");
  });

  it("holds on the daily tape in both its states", () => {
    const ready = render(
      <DailyTape
        capture={{ consecutiveDays: 52, lastCaptureAt: "2026-08-29", status: "ok" }}
        provenance={{ registryVersion: 3, modelVintage: "ok", status: "ok" }}
      />,
    );
    expectClean(ready.container, "Daily tape (fresh)");

    const degraded = render(
      <DailyTape
        capture={{ consecutiveDays: 0, lastCaptureAt: "", status: "unavailable" }}
        provenance={{
          registryVersion: 0,
          modelVintage: "unavailable",
          status: "degraded",
        }}
      />,
    );
    expectClean(degraded.container, "Daily tape (degraded)");
  });
});
