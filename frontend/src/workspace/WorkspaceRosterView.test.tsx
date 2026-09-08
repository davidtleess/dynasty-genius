// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { WorkspacePlayer } from "./types";
import { WorkspaceRosterView } from "./WorkspaceRosterView";
import { joinWorkspacePlayers } from "./workspaceData";
import { comparison, ranks } from "./workspaceFixtures";

vi.mock("./WorkspaceRosterGroups", () => ({
  WorkspaceRosterGroups: ({
    rows,
    onSelect,
    onFindAlternatives,
  }: {
    rows: WorkspacePlayer[];
    onSelect: (p: WorkspacePlayer) => void;
    onFindAlternatives: (p: string) => void;
  }) => (
    <div>
      {rows.map((p) => (
        <button type="button" key={p.id} onClick={() => onSelect(p)}>
          Select {p.name}
        </button>
      ))}
      <button type="button" onClick={() => onFindAlternatives("QB")}>
        Browse quarterbacks
      </button>
    </div>
  ),
}));
vi.mock("./WorkspaceInspector", () => ({
  WorkspaceInspector: ({
    player,
    onAlternatives,
  }: {
    player: WorkspacePlayer;
    onAlternatives: (p: WorkspacePlayer) => void;
  }) => (
    <div>
      <p>Inspecting {player.name}</p>
      <button type="button" onClick={() => onAlternatives(player)}>
        Find an alternative
      </button>
    </div>
  ),
}));
const originalDialogMethods = Object.fromEntries(
  ["showModal", "close"].map((name) => [
    name,
    Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, name),
  ]),
);
let desktop = true;
beforeEach(() => {
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({
      matches: desktop,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  );
  Object.defineProperty(HTMLDialogElement.prototype, "showModal", {
    configurable: true,
    value: function (this: HTMLDialogElement) {
      this.open = true;
    },
  });
  Object.defineProperty(HTMLDialogElement.prototype, "close", {
    configurable: true,
    value: function (this: HTMLDialogElement) {
      this.open = false;
    },
  });
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  for (const [name, descriptor] of Object.entries(originalDialogMethods)) {
    if (descriptor)
      Object.defineProperty(HTMLDialogElement.prototype, name, descriptor);
    else Reflect.deleteProperty(HTMLDialogElement.prototype, name);
  }
  desktop = true;
});
const players = joinWorkspacePlayers(ranks, comparison, new Map());
const owned = players.filter((p) => p.ownership === "roster");
const available = players.filter((p) => p.ownership === "available");
function mount(extra = {}) {
  const onComparePair = vi.fn();
  render(
    <WorkspaceRosterView
      roster={owned}
      available={available}
      data={ranks}
      nowLabel="2026"
      futureLabel="2027"
      forecastsReady
      forecastError={false}
      onWatch={vi.fn()}
      onCompare={vi.fn()}
      onComparePair={onComparePair}
      {...extra}
    />,
  );
  return { onComparePair };
}
it("starts with roster coverage and asks for selection rather than choosing a player for David", () => {
  mount();
  expect(screen.getByRole("heading", { name: "Your roster" })).toBeTruthy();
  expect(screen.getByText(/Choose a player/)).toBeTruthy();
  expect(screen.queryByText(/Inspecting/)).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Select Player owned" }));
  expect(screen.getByText("Inspecting Player owned")).toBeTruthy();
  expect(screen.queryByRole("dialog")).toBeNull();
});
it("finds same-position unowned alternatives and passes BOTH chosen ids to Compare", () => {
  const { onComparePair } = mount();
  fireEvent.click(screen.getByRole("button", { name: "Select Player owned" }));
  fireEvent.click(screen.getByRole("button", { name: "Find an alternative" }));
  expect(screen.getByLabelText("Compare against")).toHaveProperty("value", "owned");
  const incumbent = screen.getByRole("region", { name: "Your comparison player" });
  expect(within(incumbent).getByText("Player owned")).toBeTruthy();
  expect(incumbent.textContent).toMatch(/Our rank/);
  expect(incumbent.textContent).toMatch(/Market/);
  expect(screen.queryByText("Player other-manager")).toBeNull();
  expect(screen.getByText("Player missing")).toBeTruthy();
  fireEvent.click(
    screen.getByRole("button", { name: "Compare Player free with Player owned" }),
  );
  expect(onComparePair).toHaveBeenCalledWith("owned", "free");
});
it("a group-level alternatives request requires an explicit roster choice", () => {
  const { onComparePair } = mount();
  fireEvent.click(screen.getByRole("button", { name: "Browse quarterbacks" }));
  expect(screen.getByLabelText("Compare against")).toHaveProperty("value", "");
  const controls = screen.getAllByRole("button", { name: /^Compare Player/ });
  expect(controls.every((button) => (button as HTMLButtonElement).disabled)).toBe(true);
  expect(onComparePair).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("Compare against"), {
    target: { value: "owned" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Compare Player free with Player owned" }),
  );
  expect(onComparePair).toHaveBeenCalledWith("owned", "free");
});
it("does not treat unavailable forecast discovery as an empty pool", () => {
  mount({ forecastsReady: false, forecastError: true, available: [] });
  fireEvent.click(screen.getByRole("button", { name: "Browse quarterbacks" }));
  expect(
    within(screen.getByRole("region", { name: "Available QB alternatives" })).getByRole(
      "alert",
    ).textContent,
  ).toMatch(/could not be matched/);
  expect(screen.queryByText(/No unowned/)).toBeNull();
});
it("opens a phone dialog and returns focus to the selected row when it closes", () => {
  desktop = false;
  mount();
  const trigger = screen.getByRole("button", { name: "Select Player owned" });
  trigger.focus();
  fireEvent.click(trigger);
  const dialog = screen.getByRole("dialog", { name: "Roster player details" });
  expect(within(dialog).getByText("Inspecting Player owned")).toBeTruthy();
  fireEvent.click(within(dialog).getByRole("button", { name: "Close player details" }));
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(document.activeElement).toBe(trigger);
});
