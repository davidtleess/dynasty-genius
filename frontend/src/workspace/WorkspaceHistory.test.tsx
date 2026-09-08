// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { WorkspaceHistory } from "./WorkspaceHistory";
import { joinWorkspacePlayers } from "./workspaceData";
import { ranks } from "./workspaceFixtures";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
it("shows real saved dates without inventing earlier user moves or price history", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false }));
  const players = joinWorkspacePlayers(
    ranks,
    null,
    new Map([
      [
        "owned",
        {
          name: "Player owned",
          position: "QB",
          team: "MIN",
          watched_at: "2026-09-06T12:00:00Z",
        },
      ],
    ]),
  );
  render(<WorkspaceHistory players={players} />);
  expect(screen.getByText(/Player owned was added/)).toBeTruthy();
  await screen.findByText(/Dated market changes are unavailable/);
  expect(screen.queryByText(/Quiet morning/)).toBeNull();
});
it("rejects undated changes even when the source claims success", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        daily_diff: {
          market: {
            status: "ok",
            market_source: "fantasycalc_overlay",
            comparison_window: {},
            roster_deltas: [
              { sleeper_id: "owned", player_name: "Player owned", value_delta: 100 },
            ],
          },
        },
      }),
    }),
  );
  render(<WorkspaceHistory players={joinWorkspacePlayers(ranks, null, new Map())} />);
  await screen.findByText(/Dated market changes are unavailable/);
  expect(screen.queryByText("+100")).toBeNull();
});
