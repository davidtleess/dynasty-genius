import { useState } from "react";

import { type Command, CommandPalette } from "../command/CommandPalette";
import { PlayerDetailPage } from "../player/PlayerDetailPage";
import { PlayerInspector } from "../player/PlayerInspector";
import { RosterAudit } from "../roster/RosterAudit";
import { TradeLab } from "../trade/TradeLab";
import type { CatalogEntry } from "../trade/tradeState";
import { TrustConsole } from "../trust/TrustConsole";
import "./AppShell.css";
import { TrustStrip } from "./TrustStrip";

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

// North-star Decision Surfaces (01-north-star-architecture.md). Slots only in T3;
// each surface gets real content in later tasks.
const SURFACES = [
  "Rookie Board",
  "Roster Audit",
  "Trade Lab",
  "Waiver Radar",
  "League Pulse",
  "Model Trust",
  "Research Assistant",
] as const;

type Surface = (typeof SURFACES)[number];

export function AppShell() {
  const [activeSurface, setActiveSurface] = useState<Surface>(SURFACES[0]);
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
      setActiveSurface(surface);
      setFullDetailSleeperId(null);
    },
  }));

  return (
    <div className="dg-shell">
      <nav className="dg-shell__rail" aria-label="Primary surfaces">
        {SURFACES.map((surface) => (
          <button
            key={surface}
            type="button"
            className="dg-shell__nav-item"
            aria-current={activeSurface === surface ? "page" : undefined}
            onClick={() => {
              setActiveSurface(surface);
              setFullDetailSleeperId(null);
            }}
          >
            {surface}
          </button>
        ))}
      </nav>

      {/* biome-ignore lint/a11y/noInteractiveElementToNoninteractiveRole: a <header>
          is a banner landmark, not an interactive element — Biome mis-models it.
          Explicit role="banner" + aria-label gives the named landmark the AppShell
          contract test queries; <div role="banner"> trips useSemanticElements instead. */}
      <header className="dg-shell__trust" role="banner" aria-label="Trust strip">
        <TrustStrip position="QB" />
      </header>

      <main className="dg-shell__main">
        {fullDetailSleeperId ? (
          <PlayerDetailPage sleeperId={fullDetailSleeperId} />
        ) : (
          <>
            <h1 className="dg-shell__title">{activeSurface}</h1>
            {activeSurface === "Roster Audit" && <RosterAudit />}
            {activeSurface === "Trade Lab" && (
              <TradeLab onSelectPlayer={selectPlayer} />
            )}
            {activeSurface === "Model Trust" && <TrustConsole />}
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
