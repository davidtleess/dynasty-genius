import { useState } from "react";

import { type Command, CommandPalette } from "../command/CommandPalette";
import { AssetPrimitiveCapture } from "../dev/AssetPrimitiveCapture";
import { LeaguePulse } from "../league-pulse/LeaguePulse";
import { ModelScoreboard } from "../model-scoreboard/ModelScoreboard";
import { PlayerCardDrawer } from "../player/PlayerCardDrawer";
import { PlayerDetailPage } from "../player/PlayerDetailPage";
import { PlayerSelectionProvider } from "../player/playerSelection";
import { ProjectTracker } from "../project/ProjectTracker";
import { RealizedOutcomeScorecard } from "../realized-outcome/RealizedOutcomeScorecard";
import { RosterAudit } from "../roster/RosterAudit";
import { RosterCapacitySandbox } from "../roster-capacity/RosterCapacitySandbox";
import { AssetSearch } from "../trade/AssetSearch";
import { TradeLab } from "../trade/TradeLab";
import { TradePartners } from "../trade/TradePartners";
import type { CatalogEntry } from "../trade/tradeState";
import { useAssetCatalogSearch } from "../trade/useAssetCatalogSearch";
import { TrustConsole } from "../trust/TrustConsole";
import { DailyWhatChanged } from "../what-changed/DailyWhatChanged";
import "./AppShell.css";
import { DESTINATIONS, destinationForSurface } from "./destinations";
import { ParkedSurfaceCard } from "./ParkedSurfaceCard";
import { ShellStatusDrawer } from "./ShellStatusDrawer";
import { usePlayerCard } from "./usePlayerCard";
import { type Surface, useUrlSurfaceState } from "./useUrlSurfaceState";

function readSleeperId(entry: CatalogEntry): string | null {
  const ref = entry.market_ref;
  if (ref && typeof ref === "object") {
    const id = (ref as Record<string, unknown>).sleeper_id;
    if (typeof id === "string") {
      return id;
    }
  }
  const direct = entry.sleeper_id;
  return typeof direct === "string" ? direct : null;
}

// A catalog entry we can actually open: a player, carrying the sleeper id the
// player card is addressed by. Offering anything else would be a dead end —
// future picks have no card, so the global search never lists them.
function isOpenablePlayer(entry: CatalogEntry): boolean {
  return entry.kind === "player" && readSleeperId(entry) !== null;
}

const PARKED_SURFACE_NAMES = [
  "Rookie Board",
  "Waiver Radar",
  "Research Assistant",
] as const;

function isParked(surface: string): boolean {
  return (PARKED_SURFACE_NAMES as readonly string[]).includes(surface);
}

export function AppShell() {
  // H2 I1: surface selection lives in the URL (?surface=<slug>) — one
  // navigateSurface path shared by the rail, the view switcher and the palette.
  // DG-114 groups eleven of those surfaces into five destinations WITHOUT
  // touching the slugs: `destinations.ts` is the map, and every URL that
  // resolved yesterday resolves today.
  const { activeSurface, navigateSurface } = useUrlSurfaceState();
  const playerCard = usePlayerCard();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [paletteQuery, setPaletteQuery] = useState("");
  const palettePlayers = useAssetCatalogSearch(paletteQuery);

  // The active destination, or null when the surface was reached by URL alone
  // (the parked cards, the crew's Project Tracker, the capture target). In that
  // case NOTHING in the rail claims to be where you are, which is the truth.
  const activeDestination = destinationForSurface(activeSurface);

  function goToSurface(surface: Surface): void {
    // The card's history entry, if one is on top, is consumed rather than
    // pushed past — see usePlayerCard.ts. Nothing else can navigate while the
    // card is open (it is modal), but ⌘K listens on the document, so the case
    // is reachable and is handled rather than left to chance.
    const replace = playerCard.consumeHistoryEntry();
    navigateSurface(surface, { replace });
  }

  // Any surface (asset search, Trade Lab chip, a name in a table) may select a
  // player. DG-110 published that sink on a context so every surface printing a
  // name opens the same card; DG-114 makes what opens the CARD itself, in a
  // drawer, instead of a preview with a button into the card.
  function selectPlayerById(sleeperId: string, label: string): void {
    playerCard.open(sleeperId, label);
  }

  function selectPlayer(entry: CatalogEntry): void {
    if (entry.kind !== "player") {
      return;
    }
    const sleeperId = readSleeperId(entry);
    if (sleeperId === null) {
      return;
    }
    selectPlayerById(sleeperId, entry.label);
  }

  // The palette indexes what the rail indexes: the five destinations by their
  // own names, and the views inside a grouped destination so "cut list" and
  // "accuracy" still find their surface by typing. The parked surfaces and the
  // Project Tracker are in neither — David's ruling is that they leave the
  // navigation entirely and stay reachable at their URL.
  const commands: Command[] = DESTINATIONS.flatMap((destination) =>
    destination.views.map((view) => ({
      id: `surface-${view.surface.toLowerCase().replace(/\s+/g, "-")}`,
      label:
        destination.views.length === 1
          ? destination.label
          : `${destination.label} · ${view.label}`,
      run: () => goToSurface(view.surface),
    })),
  );

  // Players typed into the palette come back from the same catalog the search
  // box reads — rostered players only, so an unrostered player is not findable
  // here at all. Position and rostering manager ride along when present; a row
  // missing them shows fewer words, never an invented one.
  const playerCommands: Command[] = palettePlayers.results
    .filter(isOpenablePlayer)
    .map((entry) => {
      const meta = [
        typeof entry.position === "string" ? entry.position : null,
        typeof entry.roster_owner_name === "string" ? entry.roster_owner_name : null,
      ].filter((part): part is string => part !== null);
      return {
        id: `player-${entry.asset_id}`,
        label: meta.length > 0 ? `${entry.label} · ${meta.join(" · ")}` : entry.label,
        run: () => selectPlayer(entry),
      };
    });

  return (
    <PlayerSelectionProvider value={selectPlayerById}>
      <div className="dg-shell">
        <div className="dg-shell__rail">
          {/* One place to find any player, from any surface (DG-110). It opens
              the card and nothing else — no trade draft is touched. */}
          {/* A <search> landmark: without one the input is page content
              contained by no landmark, on every surface. */}
          <search className="dg-shell__search">
            <AssetSearch
              onSelect={selectPlayer}
              label="Find a player"
              placeholder="Find a player…"
              filter={isOpenablePlayer}
              // The catalog behind this box is ROSTERED players plus future
              // picks — not the whole tracked universe. Saying "nobody we
              // track matches that" over it was false for every unrostered
              // player the product names elsewhere (League Pulse), and for
              // every pick the filter drops.
              emptyNotice="No player on a roster in your league matches that. This box finds rostered players."
              filteredNotice="Only future picks match that. Picks are handled in Trade Lab."
            />
          </search>
          {/* ONE nav element for both breakpoints: at 390 CSS lays these five
              out as a fixed bottom tab bar. Rendering a second copy would give
              assistive tech two navigations with the same name and let them
              drift apart. */}
          <nav className="dg-shell__rail-primary" aria-label="Primary surfaces">
            {DESTINATIONS.map((destination) => (
              <button
                key={destination.label}
                type="button"
                className="dg-shell__nav-item"
                aria-current={
                  activeDestination?.label === destination.label ? "page" : undefined
                }
                onClick={() => goToSurface(destination.views[0]?.surface as Surface)}
              >
                {destination.label}
              </button>
            ))}
          </nav>
        </div>

        {/* biome-ignore lint/a11y/noInteractiveElementToNoninteractiveRole: a <header>
            is a banner landmark, not an interactive element — Biome mis-models it.
            Explicit role="banner" + aria-label gives the named landmark the AppShell
            contract test queries; <div role="banner"> trips useSemanticElements instead. */}
        <header className="dg-shell__trust" role="banner" aria-label="Trust strip">
          {/* Worklist #1 (fresh-agent reviews): the product owns the bar — a
              wordmark and ONE status pill; the model-grade strip and the
              diagnostics card live inside the pill's in-flow drawer, mounted
              and live but out of the first viewport. */}
          <span className="dg-shell__wordmark">Dynasty Genius</span>
          {/* The palette used to answer only to a keystroke nobody had been
              told about (DG-110). At 390 this is the search in the top bar. */}
          <button
            type="button"
            className="dg-shell__palette-trigger"
            onClick={() => setPaletteOpen(true)}
          >
            Search players and surfaces
            <span className="dg-shell__palette-shortcut"> ⌘K</span>
          </button>
          <ShellStatusDrawer />
        </header>

        <main className="dg-shell__main">
          <h1 className="dg-shell__title">
            {activeDestination?.label ?? activeSurface}
          </h1>
          {/* The view switcher for a destination that holds more than one
              surface. Each view IS a `?surface=` slug, so the switcher and a
              bookmark are the same navigation by two routes. */}
          {activeDestination !== null && activeDestination.views.length > 1 && (
            <nav
              className="dg-shell__views"
              aria-label={`${activeDestination.label} views`}
            >
              {activeDestination.views.map((view) => (
                <button
                  key={view.surface}
                  type="button"
                  className="dg-shell__view-item"
                  aria-current={activeSurface === view.surface ? "page" : undefined}
                  onClick={() => goToSurface(view.surface)}
                >
                  {view.label}
                </button>
              ))}
            </nav>
          )}
          {isParked(activeSurface) && <ParkedSurfaceCard surface={activeSurface} />}
          {activeSurface === "Asset Primitive Capture" && <AssetPrimitiveCapture />}
          {activeSurface === "Roster Audit" && <RosterAudit />}
          {activeSurface === "Roster Capacity" && <RosterCapacitySandbox />}
          {activeSurface === "Daily What-Changed" && (
            <DailyWhatChanged onSelectPlayer={selectPlayerById} />
          )}
          {activeSurface === "Accuracy Tracker" && (
            <div className="dg-shell__stack">
              {/* The record leads: what has actually been measured about this model,
                  market question first. The per-cohort scorecard beneath it is the
                  drill-down for a live week once one exists. */}
              <ModelScoreboard />
              <RealizedOutcomeScorecard />
            </div>
          )}
          {activeSurface === "Trade Lab" && <TradeLab onSelectPlayer={selectPlayer} />}
          {activeSurface === "Trade Partners" && <TradePartners />}
          {activeSurface === "Model Trust" && <TrustConsole />}
          {activeSurface === "Project Tracker" && <ProjectTracker />}
          {activeSurface === "League Pulse" && <LeaguePulse />}
        </main>

        {playerCard.player !== null && (
          <PlayerCardDrawer onClose={playerCard.close}>
            <PlayerDetailPage sleeperId={playerCard.player.sleeperId} />
          </PlayerCardDrawer>
        )}

        <CommandPalette
          commands={commands}
          extraCommands={playerCommands}
          // Same rule the search box follows: a failed read says it failed
          // rather than rendering a list with no players in it.
          notice={
            palettePlayers.status === "unavailable"
              ? "We could not read the player list, so no players are shown here. Surfaces still work."
              : undefined
          }
          open={paletteOpen}
          onOpenChange={setPaletteOpen}
          onQueryChange={setPaletteQuery}
        />
      </div>
    </PlayerSelectionProvider>
  );
}
