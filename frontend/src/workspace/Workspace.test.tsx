// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { MarketRanksContext } from "../market-ranks/MarketRanksContext";
import { Workspace } from "./Workspace";
import { comparison, ranks } from "./workspaceFixtures";

vi.mock("./WorkspaceFrame", () => ({
  WorkspaceFrame: ({
    children,
    onNavigate,
    onQuery,
  }: {
    children: React.ReactNode;
    onNavigate: (view: string) => void;
    onQuery: (q: string) => void;
  }) => (
    <div>
      <nav>
        {["today", "roster", "available", "watchlist", "compare", "history"].map(
          (v) => (
            <button type="button" key={v} onClick={() => onNavigate(v)}>
              {v}
            </button>
          ),
        )}
      </nav>
      <input aria-label="Find a player" onChange={(e) => onQuery(e.target.value)} />
      {children}
    </div>
  ),
}));
vi.mock("./WorkspaceBoard", () => ({
  WorkspaceBoard: ({
    rows,
    onWatch,
    onCompare,
  }: {
    rows: { id: string; name: string }[];
    onWatch: (p: unknown) => void;
    onCompare: (p: unknown) => void;
  }) => (
    <ul>
      {rows.map((p) => (
        <li key={p.id}>
          {p.name}
          <button type="button" onClick={() => onWatch(p)}>
            Watch {p.name}
          </button>
          <button type="button" onClick={() => onCompare(p)}>
            Compare {p.name}
          </button>
        </li>
      ))}
    </ul>
  ),
}));
vi.mock("./WorkspaceCompare", () => ({
  WorkspaceCompare: ({ selection }: { selection: { availableId: string | null } }) => (
    <p>Comparing {selection.availableId ?? "nobody"}</p>
  ),
}));

beforeEach(() => {
  window.history.replaceState(null, "", "/?surface=workspace&view=roster");
  window.localStorage.clear();
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, json: async () => comparison }),
  );
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
const mount = () =>
  render(
    <MarketRanksContext.Provider value={{ status: "available", data: ranks }}>
      <Workspace />
    </MarketRanksContext.Provider>,
  );
it("keeps default available missing rows, watches across navigation and opens the selected comparison", async () => {
  mount();
  fireEvent.click(screen.getByRole("button", { name: "available" }));
  await screen.findByText("Player free");
  expect(screen.getByText("Player missing")).toBeTruthy();
  expect(screen.queryByText("Player other-manager")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Watch Player missing" }));
  fireEvent.click(screen.getByRole("button", { name: "watchlist" }));
  expect(screen.getByText("Player missing")).toBeTruthy();
  expect(
    JSON.parse(window.localStorage.getItem("dg178.watchlist") ?? "{}").version,
  ).toBe(2);
  fireEvent.click(screen.getByRole("button", { name: "Compare Player missing" }));
  expect(screen.getByText("Comparing missing")).toBeTruthy();
  expect(window.location.search).toContain("view=compare");
});
it("global search finds another manager's player without claiming he is available", async () => {
  mount();
  await waitFor(() => expect(fetch).toHaveBeenCalled());
  fireEvent.change(screen.getByLabelText("Find a player"), {
    target: { value: "other-manager" },
  });
  expect(screen.getByRole("heading", { name: "Search results" })).toBeTruthy();
  expect(screen.getByText("Player other-manager")).toBeTruthy();
});
it("refuses incompatible discovery data while preserving the rank roster", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        ...comparison,
        source: { ...comparison.source, report_run: "wrong" },
      }),
    }),
  );
  mount();
  expect(screen.getByText("Player owned")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "available" }));
  await screen.findByText(/Available players and forecasts could not be matched/);
  expect(screen.queryByText("Player free")).toBeNull();
});
