import { useState } from "react";

import { type Command, CommandPalette } from "../command/CommandPalette";
import { AssetPrimitiveCapture } from "../dev/AssetPrimitiveCapture";
import { LeaguePulse } from "../league-pulse/LeaguePulse";
import { PlayerDetailPage } from "../player/PlayerDetailPage";
import { PlayerInspector } from "../player/PlayerInspector";
import { ProjectTracker } from "../project/ProjectTracker";
import { RealizedOutcomeScorecard } from "../realized-outcome/RealizedOutcomeScorecard";
import { RosterAudit } from "../roster/RosterAudit";
import { RosterCapacitySandbox } from "../roster-capacity/RosterCapacitySandbox";
import { SystemHealthCard } from "../system-health/SystemHealthCard";
import { TradeLab } from "../trade/TradeLab";
import type { CatalogEntry } from "../trade/tradeState";
import { TrustConsole } from "../trust/TrustConsole";
import { DailyWhatChanged } from "../what-changed/DailyWhatChanged";
import "./AppShell.css";
import { ParkedSurfaceCard } from "./ParkedSurfaceCard";
import { TrustStrip } from "./TrustStrip";
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
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [selectedPlayer, setSelectedPlayer] = useState<SelectedPlayer | null>(null);
  // When set, the main view shows the full Decision-Evidence-Card page for this
  // player (opened from the inspector's "Open full evidence card" action).
  const [fullDetailSleeperId, setFullDetailSleeperId] = useState<string | null>(null);

  // Any surface (asset search, Trade Lab chip) may select a player → opens the
  // inspector. Players only; non-player catalog entries are not inspectable in v1.
  // The sleeper id lives on market_ref (the catalog entry's top-level sleeper_id
  // is not part of the generated schema, so it is stripped at the Zod boundary).
  function selectPlayer(entry: CatalogEntry): void {
    if (entry.kind !== "player") {
      return;
    }
    const sleeperId = readSleeperId(entry);
    if (sleeperId === null) {
      return;
    }
    setSelectedPlayer({ sleeperId, label: entry.label });
    setInspectorOpen(true);
  }

  const commands: Command[] = SURFACES.map((surface) => ({
    id: surface.toLowerCase().replace(/\s+/g, "-"),
    label: surface,
    run: () => {
      navigateSurface(surface);
      setFullDetailSleeperId(null);
    },
  }));

  return (
    <div className="dg-shell">
      <div className="dg-shell__rail">
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
        <TrustStrip position="QB" />
        {/* Whole-app operational trust (pipeline/data freshness) — a different
            trust axis from the model-grade TrustStrip; adjacent, never merged. */}
        <SystemHealthCard />
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
            {activeSurface === "Daily What-Changed" && <DailyWhatChanged />}
            {activeSurface === "Accuracy Tracker" && <RealizedOutcomeScorecard />}
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
        {selectedPlayer && (
          <PlayerInspector
            player={selectedPlayer}
            onClose={() => setInspectorOpen(false)}
            onOpenFullDetail={() => setFullDetailSleeperId(selectedPlayer.sleeperId)}
          />
        )}
      </aside>

      <CommandPalette commands={commands} />
    </div>
  );
}
