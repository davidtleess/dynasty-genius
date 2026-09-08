// @vitest-environment jsdom
// DG-187 — the workspace shell: one rail, one search, the source dates, and the main region the
// views render into. Every number and date here comes from props; the imported design's sample
// team names, sample dates and design-review chrome are deliberately absent.
import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { auditRenderedCopy, formatRawCopyFindings } from "../lib/renderRule";
import type { WorkspaceFrameProps } from "./types";
import { WorkspaceFrame } from "./WorkspaceFrame";

const source = {
  forecastDate: "2026-09-07",
  marketDate: "2026-09-06T13:00:02.542329+00:00",
  ownershipDate: "2026-09-06T13:00:52.635970+00:00",
  commonPlayers: 388,
};

function renderFrame(over: Partial<WorkspaceFrameProps> = {}) {
  const props: WorkspaceFrameProps = {
    view: "compare",
    onNavigate: vi.fn(),
    query: "",
    onQuery: vi.fn(),
    counts: { roster: 27, available: 433, watchlist: 2 },
    source,
    children: <h1>Compare</h1>,
    ...over,
  };
  return { ...render(<WorkspaceFrame {...props} />), props };
}

const rail = () => screen.getByRole("navigation", { name: "Workspace" });

describe("WorkspaceFrame — the rail", () => {
  it("offers the six destinations in order and marks the one you are on", () => {
    renderFrame({ view: "available" });
    const labels = within(rail())
      .getAllByRole("button")
      .map((b) => b.textContent?.replace(/\s+/g, " ").trim());
    expect(labels).toEqual([
      "Today",
      "Roster 27",
      "Available 433",
      "Watchlist 2",
      "Compare",
      "What changed",
    ]);
    expect(
      within(rail()).getByRole("button", { current: "page" }).textContent,
    ).toContain("Available");
  });

  it("navigates by view key, not by label", () => {
    const { props } = renderFrame();
    fireEvent.click(within(rail()).getByRole("button", { name: /^What changed/ }));
    expect(props.onNavigate).toHaveBeenCalledWith("history");
    fireEvent.click(within(rail()).getByRole("button", { name: /^Watchlist/ }));
    expect(props.onNavigate).toHaveBeenCalledWith("watchlist");
  });

  it("shows no number at all for a count it does not know, rather than a zero", () => {
    renderFrame({ counts: { roster: null, available: null, watchlist: 0 } });
    const labels = within(rail())
      .getAllByRole("button")
      .map((b) => b.textContent?.replace(/\s+/g, " ").trim());
    expect(labels).toEqual([
      "Today",
      "Roster",
      "Available",
      "Watchlist 0",
      "Compare",
      "What changed",
    ]);
  });

  it("names the league by its verified settings and never by a sample team name", () => {
    const { container } = renderFrame();
    expect(screen.getByText("David's league")).toBeTruthy();
    expect(screen.getByText(/12-team · Superflex · full PPR/)).toBeTruthy();
    expect(screen.getByText(/no tight-end premium · title in week 17/)).toBeTruthy();
    const text = container.textContent ?? "";
    for (const sample of [
      "Woodbury Riders",
      "Redzone Champions",
      "design review",
      "sample data",
    ]) {
      expect(text).not.toContain(sample);
    }
  });
});

describe("WorkspaceFrame — where the numbers come from", () => {
  it("states both capture days and the common count from props, in readable form", () => {
    const { container } = renderFrame();
    const summary = container.querySelector(
      ".dg-workspace__source-strip",
    ) as HTMLElement;
    const text = summary.textContent ?? "";
    expect(text).toContain("Our values · Sep 7, 2026");
    expect(text).toContain("Market prices · Sep 6, 2026");
    expect(text).toContain("388 players carry both numbers");
    expect(text).not.toMatch(/2026-09-07|T13:00:02/);
  });

  it("adds the ownership date and the precise capture time when the disclosure is opened", () => {
    const { container } = renderFrame();
    fireEvent.click(
      container.querySelector(".dg-workspace__source-strip") as HTMLElement,
    );
    expect(
      screen.getByText(
        /League ownership is the roster capture dated Sep 6, 2026, 13:00 UTC/,
      ),
    ).toBeTruthy();
    expect(
      screen.getByText(
        /Market prices are the FantasyCalc capture dated Sep 6, 2026, 13:00 UTC/,
      ),
    ).toBeTruthy();
  });

  it("says the dates are not available rather than inventing any when there is no source", () => {
    const { container } = renderFrame({ source: null });
    expect(
      screen.getByText("Source dates are not available on this screen yet."),
    ).toBeTruthy();
    expect(container.textContent).not.toMatch(/Sep|players carry both/);
  });
});

describe("WorkspaceFrame — search and landmarks", () => {
  it("labels the one search affordance and reports what was typed", () => {
    const { props } = renderFrame({ query: "jean" });
    const input = screen.getByLabelText("Find a player") as HTMLInputElement;
    expect(input.value).toBe("jean");
    expect(input.getAttribute("placeholder")).toBe("Name, team, or position");
    fireEvent.change(input, { target: { value: "kraft" } });
    expect(props.onQuery).toHaveBeenCalledWith("kraft");
  });

  it("offers a skip link to the main region, which holds the view", () => {
    renderFrame({ children: <p>the view</p> });
    const skip = screen.getByRole("link", { name: "Skip to main content" });
    expect(skip.getAttribute("href")).toBe("#dg-workspace-main");
    const main = screen.getByRole("main");
    expect(main.getAttribute("id")).toBe("dg-workspace-main");
    expect(within(main).getByText("the view")).toBeTruthy();
    // the skip link is the first thing a keyboard reaches
    const focusable = Array.from(
      document.querySelectorAll<HTMLElement>("a[href],button,input,select,summary"),
    );
    expect(focusable[0]).toBe(skip);
  });

  it("owns exactly one navigation and leaves the heading to the view it frames", () => {
    const { container } = renderFrame({ children: <h1>Compare</h1> });
    expect(screen.getAllByRole("navigation")).toHaveLength(1);
    const headings = screen.getAllByRole("heading", { level: 1 });
    expect(headings).toHaveLength(1);
    expect(headings[0]?.textContent).toBe("Compare");
    // the frame itself contributes no heading outside the children
    const main = screen.getByRole("main");
    expect(container.querySelectorAll("h1").length).toBe(1);
    expect(main.contains(headings[0] as Node)).toBe(true);
  });

  it("puts no raw pipeline key or shouted token on screen", () => {
    const { container } = renderFrame();
    const findings = auditRenderedCopy(container);
    expect(findings, formatRawCopyFindings(findings)).toEqual([]);
  });
});

// DG-197 — the frame shared by all three imported Directions. David authorized implementing the
// Directions file on 2026-09-08; the MAIN composition is still his choice, so nothing below assumes
// one: no route is renamed and no initial route is picked.
describe("WorkspaceFrame — the compact header", () => {
  it("carries the one search inside the header, still controlled and still labelled the same", () => {
    const { props } = renderFrame({ query: "jean" });
    const input = screen.getByLabelText("Find a player") as HTMLInputElement;
    expect(input.closest("header")).not.toBeNull();
    expect(input.closest("main")).toBeNull();
    expect(input.value).toBe("jean");
    expect(input.getAttribute("placeholder")).toBe("Name, team, or position");
    fireEvent.change(input, { target: { value: "kraft" } });
    expect(props.onQuery).toHaveBeenCalledWith("kraft");
    // still exactly one search on the screen
    expect(screen.getAllByRole("searchbox")).toHaveLength(1);
  });

  it("offers a watchlist shortcut in the header with the real count, and navigates by view key", () => {
    const { props } = renderFrame({
      counts: { roster: 27, available: 433, watchlist: 4 },
    });
    const shortcut = screen.getByRole("button", { name: "Open watchlist" });
    expect(shortcut.closest("header")).not.toBeNull();
    expect(shortcut.textContent).toContain("4");
    fireEvent.click(shortcut);
    expect(props.onNavigate).toHaveBeenCalledWith("watchlist");
  });

  // The rule half of this lives in WorkspaceFrame.css.test.js: a `?raw` CSS import resolves to the
  // EMPTY STRING under Vitest, so every assertion made against one passes without reading anything.
  it("writes the wordmark in title case, not shouted", () => {
    const { container } = renderFrame();
    const wordmark = container.querySelector(".dg-workspace__wordmark") as HTMLElement;
    expect(wordmark.textContent).toBe("Dynasty Genius");
  });
});

describe("WorkspaceFrame — the search shortcut", () => {
  it("focuses the search on the platform shortcut, without swallowing ordinary typing", () => {
    renderFrame();
    const input = screen.getByLabelText("Find a player");
    expect(document.activeElement).not.toBe(input);

    fireEvent.keyDown(document, { key: "k", metaKey: true });
    expect(document.activeElement).toBe(input);

    (document.activeElement as HTMLElement).blur();
    fireEvent.keyDown(document, { key: "k", ctrlKey: true });
    expect(document.activeElement).toBe(input);

    // a bare k is someone typing a name, and must reach the page untouched
    (document.activeElement as HTMLElement).blur();
    fireEvent.keyDown(document, { key: "k" });
    expect(document.activeElement).not.toBe(input);
    fireEvent.keyDown(document, { key: "k", shiftKey: true });
    expect(document.activeElement).not.toBe(input);
  });

  it("removes its key listener when the frame goes away", () => {
    const add = vi.spyOn(document, "addEventListener");
    const remove = vi.spyOn(document, "removeEventListener");
    const { unmount } = renderFrame();
    const registered = add.mock.calls.filter(([type]) => type === "keydown");
    expect(registered.length).toBeGreaterThan(0);
    unmount();
    const released = remove.mock.calls.filter(([type]) => type === "keydown");
    expect(released.map(([, fn]) => fn)).toEqual(
      expect.arrayContaining(registered.map(([, fn]) => fn)),
    );
    add.mockRestore();
    remove.mockRestore();
  });
});
