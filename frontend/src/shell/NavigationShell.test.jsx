// @vitest-environment jsdom
//
// DG-114 — THE NAVIGATION SHELL (DG-091 phase 2B wave 2).
//
// David's 2026-08-30 panel, verbatim option labels: "Remove from nav entirely"
// and "Build the phone shell now". The Studio spec §4 turns those into four
// mechanical requirements, and these are the decisive checks for them:
//
//   1. the rail carries FIVE destinations, not eleven links;
//   2. the parked surfaces and the crew's Project Tracker are gone from every
//      navigation affordance — reachable at their URL and nowhere else;
//   3. every `?surface=` slug that worked yesterday still works, because this
//      is a grouping and not a router rewrite — a bookmark must not break;
//   4. a player's name opens his card in ONE press, in a drawer that Esc, the
//      close button, the scrim and browser Back all close;
//   5. at 390 the five destinations are pinned to the bottom of the viewport
//      instead of scrolling past as a wrapped link-cloud.

import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import playerDetailLive from "../lib/__fixtures__/playerDetail.live.json";
import { AppShell } from "./AppShell";

const DESTINATIONS = ["Today", "Roster", "Trades", "League", "Track record"];

// Every slug the shell answered to before this ticket. A bookmark David saved
// yesterday has to land on the same content today.
const SLUG_DESTINATION = [
  ["what-changed", "Today"],
  ["roster-audit", "Roster"],
  ["roster-capacity", "Roster"],
  ["trade-lab", "Trades"],
  ["league-pulse", "League"],
  ["model-trust", "Track record"],
  ["accuracy-tracker", "Track record"],
];

const URL_ONLY_SLUGS = [
  ["rookie-board", "Rookie Board — parked"],
  ["waiver-radar", "Waiver Radar — parked"],
  ["research-assistant", "Research Assistant — parked"],
];

// David's own captured payloads: the catalog row and the card behind it are
// the same player, so the check reads the way the product runs.
function catalogEntry(overrides = {}) {
  return {
    asset_id: "12508",
    caveats: [],
    decision_supported: false,
    kind: "player",
    label: "Jaxson Dart",
    market_ref: {
      asset_kind: "player",
      decision_supported: false,
      player_id: "12508",
      sleeper_id: "12508",
    },
    model_payload: {
      decision_supported: false,
      is_prospect: false,
      player_id: "12508",
      position: "QB",
      xvar: 10.31,
    },
    position: "QB",
    roster_owner_id: 1,
    roster_owner_name: "Dleess",
    ...overrides,
  };
}

function catalogResponse(results = [catalogEntry()]) {
  return {
    caveats: [],
    decision_supported: false,
    query: "dart",
    results,
    source_timestamp: "2026-08-29T13:00:46+00:00",
  };
}

// Anything not named degrades honestly on 503, exactly as the product does.
function mockEndpoints(routes) {
  globalThis.fetch = vi.fn().mockImplementation((input) => {
    const url = typeof input === "string" ? input : String(input);
    const key = Object.keys(routes).find((route) => url.startsWith(route));
    const body = key === undefined ? { detail: "down" } : routes[key];
    const ok = key !== undefined;
    return Promise.resolve({ ok, status: ok ? 200 : 503, json: async () => body });
  });
}

function railLabels() {
  return within(screen.getByRole("navigation", { name: "Primary surfaces" }))
    .getAllByRole("button")
    .map((button) => button.textContent.replace(/\s+/g, " ").trim());
}

function currentDestination() {
  const active = within(screen.getByRole("navigation", { name: "Primary surfaces" }))
    .getAllByRole("button")
    .filter((button) => button.getAttribute("aria-current") === "page");
  return active.map((button) => button.textContent.replace(/\s+/g, " ").trim());
}

async function openTheCard() {
  fireEvent.change(screen.getByRole("searchbox", { name: /find a player/i }), {
    target: { value: "dart" },
  });
  fireEvent.click(await screen.findByRole("button", { name: "Jaxson Dart" }));
  return await screen.findByRole("dialog", { name: "Player card" });
}

beforeEach(() => {
  localStorage.clear();
  window.history.replaceState(null, "", "/");
});

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
  window.history.replaceState(null, "", "/");
});

describe("DG-114 · the rail carries five destinations", () => {
  it("lists exactly the five destinations, in order", () => {
    mockEndpoints({});
    render(<AppShell />);

    expect(railLabels()).toEqual(DESTINATIONS);
  });

  it("leaves the parked surfaces and the crew tracker out of every navigation affordance", () => {
    mockEndpoints({});
    render(<AppShell />);

    // Not in the rail, not in a Developer zone of its own, not in the palette.
    for (const gone of [
      "Rookie Board",
      "Waiver Radar",
      "Research Assistant",
      "Project Tracker",
    ]) {
      expect(
        screen.queryByRole("button", { name: new RegExp(gone, "i") }),
        `${gone} is still a navigation target`,
      ).toBeNull();
    }
    expect(screen.queryByRole("navigation", { name: /developer/i })).toBeNull();
    expect(screen.queryByText(/\(Parked\)/)).toBeNull();

    fireEvent.keyDown(document, { key: "k", metaKey: true });
    for (const gone of [
      "Rookie Board",
      "Waiver Radar",
      "Research Assistant",
      "Project Tracker",
    ]) {
      expect(
        screen.queryByRole("option", { name: gone }),
        `${gone} is still a palette command`,
      ).toBeNull();
    }
  });
});

describe("DG-114 · a bookmark from yesterday still lands", () => {
  it.each(SLUG_DESTINATION)("?surface=%s lights %s", (slug, destination) => {
    mockEndpoints({});
    window.history.replaceState(null, "", `/?surface=${slug}`);
    render(<AppShell />);

    expect(currentDestination()).toEqual([destination]);
  });

  it.each(URL_ONLY_SLUGS)("?surface=%s still renders %s", (slug, heading) => {
    mockEndpoints({});
    window.history.replaceState(null, "", `/?surface=${slug}`);
    render(<AppShell />);

    expect(screen.getByRole("heading", { name: heading })).toBeTruthy();
    // Reached by URL, so nothing in the rail claims to be where you are.
    expect(currentDestination()).toEqual([]);
  });

  it("keeps the grouped surfaces switchable from inside their destination", async () => {
    mockEndpoints({});
    window.history.replaceState(null, "", "/?surface=roster-audit");
    render(<AppShell />);

    const views = screen.getByRole("navigation", { name: /roster views/i });
    fireEvent.click(within(views).getByRole("button", { name: "Cut list" }));

    await waitFor(() =>
      expect(window.location.search).toBe("?surface=roster-capacity"),
    );
    expect(currentDestination()).toEqual(["Roster"]);
  });
});

describe("DG-114 · a player's card opens in one press", () => {
  it("opens the full card directly, with no second step to press", async () => {
    mockEndpoints({
      "/api/trade/assets": catalogResponse(),
      "/api/players/": playerDetailLive,
    });
    render(<AppShell />);

    const drawer = await openTheCard();
    expect(
      await within(drawer).findByRole("article", {
        name: /player detail for jaxson dart/i,
      }),
    ).toBeTruthy();
    // The retired two-step: a neutral preview whose only job was to offer a
    // button into the card the press had already asked for.
    expect(
      screen.queryByRole("button", { name: /open full evidence card/i }),
    ).toBeNull();
  });

  it("closes on the close button, on Escape, on the scrim, and on browser Back", async () => {
    mockEndpoints({
      "/api/trade/assets": catalogResponse(),
      "/api/players/": playerDetailLive,
    });
    render(<AppShell />);

    const drawer = await openTheCard();
    fireEvent.click(within(drawer).getByRole("button", { name: "Close player card" }));
    await waitFor(() =>
      expect(screen.queryByRole("dialog", { name: "Player card" })).toBeNull(),
    );

    await openTheCard();
    fireEvent.keyDown(document, { key: "Escape" });
    await waitFor(() =>
      expect(screen.queryByRole("dialog", { name: "Player card" })).toBeNull(),
    );

    await openTheCard();
    fireEvent.click(document.querySelector(".dg-player-drawer__scrim"));
    await waitFor(() =>
      expect(screen.queryByRole("dialog", { name: "Player card" })).toBeNull(),
    );

    await openTheCard();
    window.dispatchEvent(new PopStateEvent("popstate"));
    await waitFor(() =>
      expect(screen.queryByRole("dialog", { name: "Player card" })).toBeNull(),
    );
  });
});

// REVIEW FIX. At 390 the rail's search box is display:none, so this palette is
// the ONLY player finder on David's phone — and it rendered an empty listbox
// and nothing else. An empty list reads as "we do not track him", which is
// false for every unrostered player the product names elsewhere. The scoping
// sentences the box has carried since DG-110 have to be reachable here too, in
// the same words, or the two finders answer the same question differently.
describe("DG-114 · the palette says what it searched", () => {
  const NO_ROSTERED_MATCH =
    "No player on a roster in your league matches that. This box finds rostered players.";

  function openPalette() {
    fireEvent.keyDown(document, { key: "k", metaKey: true });
    return screen.getByRole("textbox", { name: /command palette/i });
  }

  it("names its scope instead of returning a silent empty list", async () => {
    mockEndpoints({ "/api/trade/assets": catalogResponse([]) });
    render(<AppShell />);

    fireEvent.change(openPalette(), { target: { value: "zzzz" } });

    // No surface matches "zzzz" and the catalog answered with no players, so
    // the list is genuinely empty — the case that used to say nothing at all.
    expect(await screen.findByText(NO_ROSTERED_MATCH)).toBeTruthy();
    await waitFor(() =>
      expect(within(screen.getByRole("listbox")).queryAllByRole("option")).toHaveLength(
        0,
      ),
    );
  });

  it("says the same sentence the rail's box says, not a second version of it", async () => {
    mockEndpoints({ "/api/trade/assets": catalogResponse([]) });
    render(<AppShell />);

    fireEvent.change(screen.getByRole("searchbox", { name: /find a player/i }), {
      target: { value: "zzzz" },
    });
    expect(await screen.findByText(NO_ROSTERED_MATCH)).toBeTruthy();

    fireEvent.change(openPalette(), { target: { value: "zzzz" } });
    // Both finders on screen, one sentence between them — they read the same
    // module constant, so they cannot drift into two different answers.
    await waitFor(() => expect(screen.getAllByText(NO_ROSTERED_MATCH)).toHaveLength(2));
  });

  it("does not claim 'no match' while the catalog has not been asked", () => {
    mockEndpoints({ "/api/trade/assets": catalogResponse([]) });
    render(<AppShell />);

    // Under the 3-character minimum the search never runs, so a "nothing
    // matches" sentence would be a claim nobody made. It states the rule.
    fireEvent.change(openPalette(), { target: { value: "zz" } });

    expect(screen.queryByText(NO_ROSTERED_MATCH)).toBeNull();
    expect(screen.getByText("Type at least 3 letters to search players.")).toBeTruthy();
  });

  it("keeps Escape to one layer: the palette closes, the card behind it stays", async () => {
    mockEndpoints({
      "/api/trade/assets": catalogResponse(),
      "/api/players/": playerDetailLive,
    });
    render(<AppShell />);

    await openTheCard();
    const input = openPalette();
    fireEvent.keyDown(input, { key: "Escape" });

    // Measured before the fix: one press left {palette:false, drawer:false}.
    // The drawer listens on `document`, which is the last stop a keydown
    // reaches, so the topmost layer stops the event first.
    expect(screen.queryByRole("textbox", { name: /command palette/i })).toBeNull();
    expect(screen.getByRole("dialog", { name: "Player card" })).toBeTruthy();
  });
});

describe("DG-114 · the phone shell", () => {
  const shellCss = readFileSync(
    resolve(dirname(fileURLToPath(import.meta.url)), "AppShell.css"),
    "utf8",
  );

  /** The ≤768px block, brace-matched so nested rules come with it. */
  function phoneBlock(css) {
    const start = css.search(/@media\s*\(max-width:\s*768px\)/);
    expect(start, "AppShell.css must carry a phone block").toBeGreaterThan(-1);
    let depth = 0;
    for (let i = css.indexOf("{", start); i < css.length; i += 1) {
      if (css[i] === "{") depth += 1;
      if (css[i] === "}") {
        depth -= 1;
        if (depth === 0) return css.slice(start, i + 1);
      }
    }
    throw new Error("unterminated phone block");
  }

  it("pins the five destinations to the bottom of the viewport instead of scrolling them past", () => {
    const phone = phoneBlock(shellCss);

    // The defect: ~430px of wrapped link-cloud chrome scrolled past before any
    // content appeared. A tab bar is fixed to the bottom edge and stays there.
    expect(phone).toMatch(/\.dg-shell__rail-primary\s*\{[^}]*position:\s*fixed[^}]*\}/);
    expect(phone).toMatch(/\.dg-shell__rail-primary\s*\{[^}]*inset-block-end:\s*0/);

    // Content has to clear it, or the tab bar sits on top of the last row.
    //
    // The first cut of this check asserted only that `padding-block-end`
    // EXISTS, and it passed while the product did the wrong thing: the bar was
    // content-box, so a 60px minimum plus 4+4 padding and a 1px border rendered
    // 69px against a 60px reserve, and the last 9px of every phone surface —
    // the whole of the front page's "Report built …" receipt line — sat under
    // an opaque bar. Measured in Chromium at 320/360/390/430/600/768.
    //
    // A stylesheet cannot be measured from here, so what this pins is the pair
    // of rules that make the number true: ONE token for both, and a border-box
    // bar so the token is the bar's whole height and not just its content.
    expect(phone).toMatch(
      /\.dg-shell__rail-primary\s*\{[^}]*box-sizing:\s*border-box[^}]*\}/,
    );
    expect(phone).toMatch(
      /\.dg-shell__rail-primary\s*\{[^}]*min-block-size:\s*var\(--dg-shell-tabbar\)[^}]*\}/,
    );
    expect(phone).toMatch(
      /\.dg-shell__main\s*\{[^}]*padding-block-end:\s*var\(--dg-shell-tabbar\)[^}]*\}/,
    );
    // 61px = 1px border + 4px + a 52px touch target + 4px. Measured on the
    // served bundle at 390x844: bar height 61, main padding-bottom 61px, and
    // the last line of the front page fully clear of the bar.
    expect(shellCss).toMatch(/--dg-shell-tabbar:\s*3\.8125rem/);
  });

  it("gives phone rows the 52px touch target the spec asks for", () => {
    // On the ROW. Two earlier cuts were measured in Chromium and neither
    // produced 52: `min-block-size` on the cells gave 30px rows (min-height on
    // a table cell is undefined and Chromium ignores it) and `padding-block`
    // gave 51px on the 13px tables. `block-size` on a table row is defined as a
    // minimum, and measures exactly 52px on Roster and Track record at 390.
    expect(phoneBlock(shellCss)).toMatch(/tbody tr\s*\{[^}]*block-size:\s*52px/);
  });
});
