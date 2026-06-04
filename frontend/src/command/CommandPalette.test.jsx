// @vitest-environment jsdom

import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CommandPalette } from "./CommandPalette";

function renderPalette() {
  const commands = [
    { id: "rookie-board", label: "Rookie Board", run: vi.fn() },
    { id: "trade-lab", label: "Trade Lab", run: vi.fn() },
    { id: "research-assistant", label: "Research Assistant", run: vi.fn() },
  ];

  render(<CommandPalette commands={commands} />);

  return { commands };
}

function openPalette() {
  fireEvent.keyDown(document, { key: "k", metaKey: true });
  return screen.getByRole("textbox", { name: "Command palette" });
}

function optionByName(name) {
  return screen.getByRole("option", { name });
}

describe("CommandPalette", () => {
  it("opens with Cmd+K and exposes the searchable command list", () => {
    renderPalette();

    expect(screen.queryByRole("textbox", { name: "Command palette" })).toBeNull();

    openPalette();

    const listbox = screen.getByRole("listbox", { name: "Commands" });
    expect(within(listbox).getByRole("option", { name: "Rookie Board" })).toBeTruthy();
    expect(within(listbox).getByRole("option", { name: "Trade Lab" })).toBeTruthy();
  });

  it("filters commands by typed text with hand-rolled matching", () => {
    renderPalette();
    const search = openPalette();

    fireEvent.change(search, { target: { value: "trade" } });

    expect(optionByName("Trade Lab")).toBeTruthy();
    expect(screen.queryByRole("option", { name: "Rookie Board" })).toBeNull();
    expect(screen.queryByRole("option", { name: "Research Assistant" })).toBeNull();
  });

  it("runs the active command with Enter and closes", () => {
    const { commands } = renderPalette();
    const search = openPalette();

    fireEvent.change(search, { target: { value: "trade" } });
    fireEvent.keyDown(search, { key: "Enter" });

    expect(commands[1].run).toHaveBeenCalledTimes(1);
    expect(commands[0].run).not.toHaveBeenCalled();
    expect(screen.queryByRole("textbox", { name: "Command palette" })).toBeNull();
  });

  it("closes with Escape without running a command", () => {
    const { commands } = renderPalette();
    const search = openPalette();

    fireEvent.keyDown(search, { key: "Escape" });

    expect(commands[0].run).not.toHaveBeenCalled();
    expect(commands[1].run).not.toHaveBeenCalled();
    expect(commands[2].run).not.toHaveBeenCalled();
    expect(screen.queryByRole("textbox", { name: "Command palette" })).toBeNull();
  });

  it("moves the active command with ArrowDown and ArrowUp", () => {
    renderPalette();
    const search = openPalette();

    expect(optionByName("Rookie Board").getAttribute("aria-selected")).toBe("true");

    fireEvent.keyDown(search, { key: "ArrowDown" });

    expect(optionByName("Rookie Board").getAttribute("aria-selected")).toBe("false");
    expect(optionByName("Trade Lab").getAttribute("aria-selected")).toBe("true");

    fireEvent.keyDown(search, { key: "ArrowUp" });

    expect(optionByName("Rookie Board").getAttribute("aria-selected")).toBe("true");
    expect(optionByName("Trade Lab").getAttribute("aria-selected")).toBe("false");
  });
});
