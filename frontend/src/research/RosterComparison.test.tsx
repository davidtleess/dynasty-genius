// @vitest-environment jsdom
// DG-181 — the roster-spot comparison: pick one available player and one you own, see 2026 and
// 2027–2030 apart, with honest wording for ties, near-ties, missing values, starting estimates
// and cross-position pairs. Fixtures are real catalog/report identities (RosterComparison.fixtures).
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  type ComparisonSelection,
  EMPTY_SELECTION,
  RosterComparison,
} from "./RosterComparison";
import { comparisonPayload } from "./RosterComparison.fixtures";

function Harness({ initial = EMPTY_SELECTION }: { initial?: ComparisonSelection }) {
  const [sel, setSel] = useState<ComparisonSelection>(initial);
  return <RosterComparison selection={sel} onSelect={setSel} />;
}

function mockFetch(body: unknown = comparisonPayload) {
  const fetchMock = vi.fn(async () => ({ ok: true, json: async () => body }));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.restoreAllMocks();
  window.history.replaceState(null, "", "/");
});

const availableInput = () =>
  screen.getByLabelText("Available player") as HTMLInputElement;
const rosterInput = () => screen.getByLabelText("Your player") as HTMLInputElement;
const pair = () => screen.getByRole("group", { name: "The two players side by side" });
const seasonsTable = () => screen.getByRole("region", { name: "Season by season" });

async function pickBoth(availableName: string, rosterName: string) {
  fireEvent.change(availableInput(), { target: { value: availableName.slice(0, 4) } });
  fireEvent.click(
    await screen.findByRole("button", { name: `Choose ${availableName}` }),
  );
  fireEvent.click(screen.getByRole("button", { name: `Choose ${rosterName}` }));
}

describe("RosterComparison — loading, error, empty, and the request it makes", () => {
  it("shows a loading line, then a plain error from the API's own detail", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false,
        status: 404,
        json: async () => ({
          detail: "no research run named x under the runs directory",
        }),
      })),
    );
    render(<Harness />);
    expect(screen.getByText("Loading the comparison…")).toBeTruthy();
    expect(
      await screen.findByText(
        "No comparison to show: no research run named x under the runs directory",
      ),
    ).toBeTruthy();
  });

  it("says which list is empty instead of offering a half comparison", async () => {
    mockFetch({ ...comparisonPayload, roster: [] });
    render(<Harness />);
    expect(
      await screen.findByText(
        "The comparison has no players to offer: your roster list is empty in this catalog.",
      ),
    ).toBeTruthy();
  });

  it("passes the page's run and catalog parameters through to the comparison endpoint", async () => {
    window.history.replaceState(
      null,
      "",
      "?surface=research-preview&tab=compare&run=20260906T214512Z&catalog=20260907T013635Z",
    );
    const fetchMock = mockFetch();
    render(<Harness />);
    await screen.findByLabelText("Available player");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/research/comparison?run=20260906T214512Z&catalog=20260907T013635Z",
    );
  });
});

describe("RosterComparison — choosing two players", () => {
  it("nominates nobody by default, finds an available player by search, lists the whole roster, and compares two quarterbacks with exact signed arithmetic", async () => {
    mockFetch();
    render(<Harness />);
    const input = await screen.findByLabelText("Available player");
    // no available player is offered until David types; nothing is nominated for him
    expect(screen.queryByRole("list", { name: "Available players" })).toBeNull();
    expect(
      screen.queryByRole("button", { name: "Change Available player" }),
    ).toBeNull();
    expect(screen.getByText("Type to search the 7 available players.")).toBeTruthy();
    fireEvent.change(input, { target: { value: "flac" } });
    const options = within(
      screen.getByRole("list", { name: "Available players" }),
    ).getAllByRole("button");
    expect(options.map((b) => b.getAttribute("aria-label"))).toEqual([
      "Choose Joe Flacco",
    ]);
    fireEvent.click(options[0] as HTMLElement);
    expect(
      screen.getByRole("button", { name: "Change Available player" }),
    ).toBeTruthy();
    expect(
      screen.getByText("Pick the other player to see the two forecasts together."),
    ).toBeTruthy();
    // the roster is small enough to list whole, alphabetically — an order, not a ranking
    expect(
      within(screen.getByRole("list", { name: "Your players" }))
        .getAllByRole("button")
        .map((b) => b.getAttribute("aria-label")),
    ).toEqual([
      "Choose J.J. McCarthy",
      "Choose Mac Jones",
      "Choose Rasheen Ali",
      "Choose Tank Dell",
      "Choose Tie Twin",
    ]);
    fireEvent.click(screen.getByRole("button", { name: "Choose J.J. McCarthy" }));
    const p = pair();
    expect(within(p).getByText("Joe Flacco")).toBeTruthy();
    expect(within(p).getByText("J.J. McCarthy")).toBeTruthy();
    expect(within(p).getByText("115.3")).toBeTruthy();
    expect(within(p).getByText("156.6")).toBeTruthy();
    expect(within(p).getByText("179.4")).toBeTruthy();
    expect(within(p).getByText("832.3")).toBeTruthy();
    const headline = screen.getByRole("status");
    expect(headline.textContent).toContain(
      "For 2026, Joe Flacco's forecast is lower than J.J. McCarthy's by 41.3 points (115.3 vs 156.6).",
    );
    expect(headline.textContent).toContain(
      "For 2027–2030, Joe Flacco's forecast is lower than J.J. McCarthy's by 652.8 points (179.4 vs 832.3).",
    );
    expect(
      screen.getByText(
        "Projected production; your lineup and roster needs still matter.",
      ),
    ).toBeTruthy();
    const t = seasonsTable();
    expect(
      within(t).getByRole("columnheader", {
        name: "Difference Joe Flacco minus J.J. McCarthy",
      }),
    ).toBeTruthy();
    const row2026 = within(t).getByRole("row", { name: /^2026/ });
    expect(within(row2026).getByText("-41.3")).toBeTruthy();
    // once both are chosen the pickers collapse to one compact line each: the full identity,
    // status and numbers live in the pair, not twice on the screen
    expect(document.querySelectorAll(".dg-ui-player-id__name")).toHaveLength(2);
    expect(screen.getAllByText("on your roster")).toHaveLength(1);
  });

  it("tells the truth when the roster list is capped and still finds every roster player by search", async () => {
    const big = {
      ...comparisonPayload,
      roster: Array.from({ length: 27 }, (_, i) => ({
        ...comparisonPayload.roster[0],
        sleeper_id: `r${i}`,
        name: `Roster Player ${String(i).padStart(2, "0")}`,
      })),
    };
    mockFetch(big);
    render(<Harness />);
    await screen.findByLabelText("Your player");
    expect(
      screen.getByText("Showing 12 of 27, A to Z; search to find the rest."),
    ).toBeTruthy();
    expect(
      screen.getAllByRole("button", { name: /^Choose Roster Player/ }),
    ).toHaveLength(12);
    fireEvent.change(rosterInput(), { target: { value: "player 26" } });
    expect(
      screen.getByRole("button", { name: "Choose Roster Player 26" }),
    ).toBeTruthy();
    expect(screen.getByText("1 match.")).toBeTruthy();
  });

  it("switching a pick removes the previous player's numbers and turns a cross-position pair into two forecasts with no winner", async () => {
    mockFetch();
    render(<Harness />);
    await screen.findByLabelText("Available player");
    await pickBoth("Joe Flacco", "J.J. McCarthy");
    expect(within(pair()).getByText("156.6")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Change Your player" }));
    fireEvent.click(screen.getByRole("button", { name: "Choose Rasheen Ali" }));
    const p = pair();
    expect(within(p).queryByText("J.J. McCarthy")).toBeNull();
    expect(within(p).queryByText("156.6")).toBeNull();
    expect(within(p).getByText("Rasheen Ali")).toBeTruthy();
    expect(within(p).getByText("52.1")).toBeTruthy();
    const headline = screen.getByRole("status");
    expect(headline.textContent).toBe(
      "Different positions (QB vs RB): raw point totals alone do not settle this roster choice.",
    );
    expect(headline.textContent).not.toMatch(/higher|lower/);
    expect(
      within(seasonsTable()).queryByRole("columnheader", { name: /^Difference/ }),
    ).toBeNull();
  });

  it("calls an exact tie a tie and names a difference under one point", async () => {
    mockFetch();
    render(<Harness />);
    await screen.findByLabelText("Available player");
    await pickBoth("Joe Flacco", "Tie Twin");
    const headline = screen.getByRole("status");
    expect(headline.textContent).toContain(
      "For 2026, the two forecasts are an exact tie (115.3 vs 115.3).",
    );
    expect(headline.textContent).toContain(
      "For 2027–2030, Joe Flacco's forecast is lower than Tie Twin's by 0.03 points (179.4 vs 179.5), a difference under one point.",
    );
  });

  it("keeps exactly one live status region once both players are chosen", async () => {
    mockFetch();
    render(<Harness />);
    await screen.findByLabelText("Available player");
    await pickBoth("Joe Flacco", "J.J. McCarthy");
    expect(screen.getAllByRole("status")).toHaveLength(1);
  });
});

describe("RosterComparison — missing, starting, zero", () => {
  it("shows a missing forecast as missing with the producer's reason and offers no comparison for that period", async () => {
    mockFetch();
    render(<Harness />);
    await screen.findByLabelText("Available player");
    await pickBoth("Carter Bradley", "J.J. McCarthy");
    const p = pair();
    const side = within(p).getByRole("group", {
      name: "Available player: Carter Bradley",
    });
    expect(within(side).getAllByText("—")).toHaveLength(2);
    expect(
      within(side).getAllByText(
        "no forecast from the selected producers; no reason stated",
      ),
    ).toHaveLength(2);
    const headline = screen.getByRole("status");
    expect(headline.textContent).toContain(
      "No 2026 forecast for Carter Bradley, so no comparison for that period.",
    );
    expect(headline.textContent).toContain(
      "No 2027–2030 forecast for Carter Bradley, so no comparison for that period.",
    );
    const row = within(seasonsTable()).getByRole("row", { name: /^2028/ });
    expect(within(row).getAllByText("—")).toHaveLength(2); // his cell and the difference
    fireEvent.click(screen.getByText("What these forecasts are, and what is missing"));
    expect(
      screen.getByText(
        /Carter Bradley: No forecast on file\. Missing: no forecast from the selected producers; no reason stated\./,
      ),
    ).toBeTruthy();
  });

  it("names both players when neither has a forecast for the period", async () => {
    mockFetch();
    render(<Harness />);
    await screen.findByLabelText("Available player");
    await pickBoth("Andrew Armstrong", "Tank Dell");
    expect(screen.getByRole("status").textContent).toContain(
      "No 2026 forecast for Andrew Armstrong or Tank Dell, so no comparison for that period.",
    );
  });

  it("labels a starting estimate, keeps a negative 2026 value's sign, and says where each year's number came from", async () => {
    mockFetch();
    render(<Harness />);
    await screen.findByLabelText("Available player");
    await pickBoth("Kurtis Rourke", "J.J. McCarthy");
    const side = within(pair()).getByRole("group", {
      name: "Available player: Kurtis Rourke",
    });
    expect(within(side).getByText("active · starting estimate")).toBeTruthy();
    expect(within(side).getByText("-0.2")).toBeTruthy();
    const t = seasonsTable();
    expect(
      within(within(t).getByRole("row", { name: /^2026/ })).getByText(
        "draft-based starting estimate",
      ),
    ).toBeTruthy();
    expect(
      within(within(t).getByRole("row", { name: /^2027/ })).getByText(
        "historical position average",
      ),
    ).toBeTruthy();
    expect(
      screen.getByText(
        /Kurtis Rourke: Starting estimate: 2026 from the draft-capital candidate/,
      ),
    ).toBeTruthy();
  });

  it("prints an exact zero as 0.0 and an absent value as missing, never the same", async () => {
    mockFetch();
    render(<Harness />);
    await screen.findByLabelText("Available player");
    await pickBoth("Zero Case", "J.J. McCarthy");
    const side = within(pair()).getByRole("group", {
      name: "Available player: Zero Case",
    });
    expect(within(side).getByText("0.0")).toBeTruthy();
    expect(within(side).getByText("—")).toBeTruthy();
    expect(within(side).getByText("no value")).toBeTruthy();
  });
});

// Root's 390x844 finding (DG-180 run 20260907T101445Z): the chooser rows and a four-line lede pushed
// the second player's numbers under the bottom nav. Once both are chosen the pair must lead.
describe("RosterComparison — the pair leads once both players are chosen", () => {
  it("drops the chooser rows, shortens the lede to one football sentence, and keeps Change on each card", async () => {
    mockFetch();
    render(<Harness />);
    await screen.findByLabelText("Available player");
    expect(
      screen.getByText(/^Pick one available player and one player you own\./),
    ).toBeTruthy();
    await pickBoth("Joe Flacco", "J.J. McCarthy");
    // no chooser inputs, no collapsed chooser rows — only the two cards carry identity
    expect(screen.queryByLabelText("Available player")).toBeNull();
    expect(screen.queryByLabelText("Your player")).toBeNull();
    expect(screen.queryByText("Available player")).toBeNull();
    expect(screen.queryByText("Your player")).toBeNull();
    expect(
      screen.getByText(
        "2026 is one season's forecast; 2027–2030 is four seasons added together.",
      ),
    ).toBeTruthy();
    expect(screen.queryByText(/^Pick one available player/)).toBeNull();
    // the pair precedes the sentence in the document, so it is what a phone shows first
    const p = pair();
    const headline = screen.getByRole("status");
    expect(
      p.compareDocumentPosition(headline) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(
      within(p).getByRole("button", { name: "Change Available player" }),
    ).toBeTruthy();
    expect(within(p).getByRole("button", { name: "Change Your player" })).toBeTruthy();
  });

  it("Change on a card reopens only that side's chooser, above the pair, and the numbers stay on screen while choosing", async () => {
    mockFetch();
    render(<Harness />);
    await screen.findByLabelText("Available player");
    await pickBoth("Joe Flacco", "J.J. McCarthy");
    fireEvent.click(within(pair()).getByRole("button", { name: "Change Your player" }));
    const input = screen.getByLabelText("Your player");
    expect(screen.queryByLabelText("Available player")).toBeNull();
    const p = pair();
    expect(within(p).getByText("156.6")).toBeTruthy();
    expect(
      input.compareDocumentPosition(p) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Choose Mac Jones" }));
    expect(screen.queryByLabelText("Your player")).toBeNull();
    expect(within(pair()).getByText("Mac Jones")).toBeTruthy();
    expect(within(pair()).queryByText("156.6")).toBeNull();
  });
});

describe("RosterComparison — saved-roster context", () => {
  it("labels a roster player the saved roster keeps on taxi or IR, and nobody else", async () => {
    mockFetch();
    render(<Harness />);
    await screen.findByLabelText("Available player");
    await pickBoth("Joe Flacco", "Tank Dell");
    const p = pair();
    const dellSide = within(p).getByRole("group", { name: "Your player: Tank Dell" });
    expect(within(dellSide).getByText("Taxi / IR in saved roster")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Change Your player" }));
    fireEvent.click(screen.getByRole("button", { name: "Choose J.J. McCarthy" }));
    expect(screen.queryByText("Taxi / IR in saved roster")).toBeNull();
  });
});

describe("RosterComparison — entry from a row", () => {
  it("keeps a player opened from outside the default pool, labels him, and does not offer him in the default search", async () => {
    mockFetch();
    render(<Harness initial={{ availableId: "11065", rosterId: null }} />);
    expect(
      await screen.findByRole("button", { name: "Change Available player" }),
    ).toBeTruthy();
    expect(screen.getByText("Adrian Martinez")).toBeTruthy();
    expect(
      screen.getByText(
        "cut · outside the default available pool; pickup eligibility not asserted",
      ),
    ).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Change Available player" }));
    fireEvent.change(availableInput(), { target: { value: "mart" } });
    expect(screen.getByText('No available player matches "mart".')).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Choose Adrian Martinez" })).toBeNull();
  });

  it("refuses an id that is not an available choice, says why, and leaves the roster picker usable", async () => {
    mockFetch();
    render(<Harness initial={{ availableId: "nope", rosterId: null }} />);
    expect(
      await screen.findByText(
        "That player is not an available choice in this catalog (owned in your league, or identity unresolved). Pick an available player.",
      ),
    ).toBeTruthy();
    expect(availableInput()).toBeTruthy();
    expect(rosterInput()).toBeTruthy();
    expect(screen.getByRole("button", { name: "Choose Mac Jones" })).toBeTruthy();
  });
});

describe("RosterComparison — evidence disclosure", () => {
  it("humanizes the dates and keeps run ids and hashes inside the disclosure only", async () => {
    mockFetch();
    render(<Harness />);
    await screen.findByLabelText("Available player");
    await pickBoth("Joe Flacco", "J.J. McCarthy");
    const details = screen
      .getByText("What these forecasts are, and what is missing")
      .closest("details") as HTMLElement;
    expect(
      within(details).getByText(
        /Ownership as of Sep 6, 2026, 13:00 UTC; NFL status as of Sep 6, 2026, 11:28 UTC\. Both may have changed since\./,
      ),
    ).toBeTruthy();
    expect(
      within(details).getByText(
        "Research PPR over the championship window (weeks 1–17); not your league's exact scoring.",
      ),
    ).toBeTruthy();
    for (const token of [/20260906T214512Z/, /20260907T013635Z/, /19e032a4067d/]) {
      const hits = screen.getAllByText(token);
      expect(hits.length).toBeGreaterThan(0);
      for (const h of hits) expect(h.closest("details")).toBe(details);
    }
    expect(within(pair()).queryByText(/20260906T214512Z/)).toBeNull();
    await waitFor(() =>
      expect(screen.getByRole("status").textContent).not.toMatch(/2026090/),
    );
  });
});
