import { useState } from "react";

import { type Command, CommandPalette } from "../command/CommandPalette";
import { AssetPrimitiveCapture } from "../dev/AssetPrimitiveCapture";
import { LeaguePulse } from "../league-pulse/LeaguePulse";
import { ModelScoreboard } from "../model-scoreboard/ModelScoreboard";
import { PlayerDetailPage } from "../player/PlayerDetailPage";
import { PlayerInspector } from "../player/PlayerInspector";
import { PlayerSelectionProvider } from "../player/playerSelection";
import { ProjectTracker } from "../project/ProjectTracker";
import { RealizedOutcomeScorecard } from "../realized-outcome/RealizedOutcomeScorecard";
import { RosterAudit } from "../roster/RosterAudit";
import { RosterCapacitySandbox } from "../roster-capacity/RosterCapacitySandbox";
import { AssetSearch } from "../trade/AssetSearch";
import { TradeLab } from "../trade/TradeLab";
import type { CatalogEntry } from "../trade/tradeState";
import { useAssetCatalogSearch } from "../trade/useAssetCatalogSearch";
import { TrustConsole } from "../trust/TrustConsole";
import { DailyWhatChanged } from "../what-changed/DailyWhatChanged";
import "./AppShell.css";
import { ParkedSurfaceCard } from "./ParkedSurfaceCard";
import { ShellStatusDrawer } from "./ShellStatusDrawer";
import { useUrlSurfaceState } from "./useUrlSurfaceState";

type SelectedPlayer = { sleeperId: string; label: string };

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

// North-star Decision Surfaces (01-north-star-architecture.md), H1 daily-login
// order (spec 2026-07-05 §1a/1b): active surfaces first, parked last (visible
// with a "Parked" badge — hiding them would hide honest gaps), and the
// Project Tracker dev utility in a separated Developer zone, out of the
// primary rail.
const ACTIVE_SURFACES = [
  "Daily What-Changed",
  "Roster Audit",
  "Trade Lab",
  "Roster Capacity",
  "League Pulse",
  "Model Trust",
  "Accuracy Tracker",
] as const;

const PARKED_SURFACE_NAMES = [
  "Rookie Board",
  "Waiver Radar",
  "Research Assistant",
] as const;

const DEVELOPER_SURFACES = ["Project Tracker"] as const;

const SURFACES = [
  ...ACTIVE_SURFACES,
  ...PARKED_SURFACE_NAMES,
  ...DEVELOPER_SURFACES,
] as const;

function isParked(surface: string): boolean {
  return (PARKED_SURFACE_NAMES as readonly string[]).includes(surface);
}

export function AppShell() {
  // H2 I1: surface selection lives in the URL (?surface=<slug>) — one
  // navigateSurface path shared by the rail and the command palette.
  const { activeSurface, navigateSurface } = useUrlSurfaceState();
  // DG-110: the inspector opens when there is a player to inspect. It used to
  // start open and empty, which read as a broken panel on every first load.
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [selectedPlayer, setSelectedPlayer] = useState<SelectedPlayer | null>(null);
  // When set, the main view shows the full Decision-Evidence-Card page for this
  // player (opened from the inspector's "Open full evidence card" action).
  const [fullDetailSleeperId, setFullDetailSleeperId] = useState<string | null>(null);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [paletteQuery, setPaletteQuery] = useState("");
  const palettePlayers = useAssetCatalogSearch(paletteQuery);

  // Any surface (asset search, Trade Lab chip) may select a player → opens the
  // inspector. Players only; non-player catalog entries are not inspectable in v1.
  // The sleeper id lives on market_ref (the catalog entry's top-level sleeper_id
  // is not part of the generated schema, so it is stripped at the Zod boundary).
  // DG-089: one selection sink for every surface — catalog entries (Trade Lab,
  // asset search) and the change feed's mover rows land in the same inspector.
  // DG-110: that sink is now published on a context, so every surface printing
  // a player's name opens the same card without new prop plumbing.
  function selectPlayerById(sleeperId: string, label: string): void {
    setSelectedPlayer({ sleeperId, label });
    setInspectorOpen(true);
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

  const commands: Command[] = SURFACES.map((surface) => ({
    id: surface.toLowerCase().replace(/\s+/g, "-"),
    label: surface,
    run: () => {
      navigateSurface(surface);
      setFullDetailSleeperId(null);
    },
  }));

  // Players typed into the palette come back from the same catalog the search
  // box reads. Position and rostering team ride along when the catalog carries
  // them; an unrostered player simply shows fewer words, never an invented one.
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
          <div className="dg-shell__search">
            <AssetSearch
              onSelect={selectPlayer}
              label="Find a player"
              placeholder="Find a player…"
              filter={isOpenablePlayer}
            />
          </div>
          <nav className="dg-shell__rail-primary" aria-label="Primary surfaces">
            {[...ACTIVE_SURFACES, ...PARKED_SURFACE_NAMES].map((surface) => (
              <button
                key={surface}
                type="button"
                className="dg-shell__nav-item"
                data-parked={isParked(surface) ? "true" : undefined}
                aria-current={activeSurface === surface ? "page" : undefined}
                onClick={() => {
                  navigateSurface(surface);
                  setFullDetailSleeperId(null);
                }}
              >
                {surface}
                {isParked(surface) && (
                  <span className="dg-shell__parked-badge"> (Parked)</span>
                )}
              </button>
            ))}
          </nav>
          {/* Dev utility zone — visually separated, out of the primary rail
              (H1 §1b): the primary rail is David-facing surfaces only. */}
          <nav className="dg-shell__developer" aria-label="Developer">
            <span className="dg-shell__developer-label">Developer</span>
            {DEVELOPER_SURFACES.map((surface) => (
              <button
                key={surface}
                type="button"
                className="dg-shell__nav-item dg-shell__nav-item--developer"
                aria-current={activeSurface === surface ? "page" : undefined}
                onClick={() => {
                  navigateSurface(surface);
                  setFullDetailSleeperId(null);
                }}
              >
                {surface}
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
              told about (DG-110). */}
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
          {fullDetailSleeperId ? (
            <PlayerDetailPage sleeperId={fullDetailSleeperId} />
          ) : (
            <>
              <h1 className="dg-shell__title">{activeSurface}</h1>
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
              {activeSurface === "Trade Lab" && (
                <TradeLab onSelectPlayer={selectPlayer} />
              )}
              {activeSurface === "Model Trust" && <TrustConsole />}
              {activeSurface === "Project Tracker" && <ProjectTracker />}
              {activeSurface === "League Pulse" && <LeaguePulse />}
            </>
          )}
        </main>

        <aside
          className="dg-shell__inspector"
          aria-label="Player inspector"
          data-state={inspectorOpen ? "open" : "closed"}
        >
          <button
            type="button"
            className="dg-shell__inspector-toggle"
            aria-label="Toggle player inspector"
            onClick={() => setInspectorOpen((open) => !open)}
          >
            Inspector
          </button>
          {selectedPlayer ? (
            <PlayerInspector
              player={selectedPlayer}
              onClose={() => setInspectorOpen(false)}
              onOpenFullDetail={() => setFullDetailSleeperId(selectedPlayer.sleeperId)}
            />
          ) : (
            <p className="dg-shell__inspector-empty">
              No player picked yet. Search above, or click any player's name.
            </p>
          )}
        </aside>

        <CommandPalette
          commands={commands}
          extraCommands={playerCommands}
          open={paletteOpen}
          onOpenChange={setPaletteOpen}
          onQueryChange={setPaletteQuery}
        />
      </div>
    </PlayerSelectionProvider>
  );
}
