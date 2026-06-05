import { useState } from "react";

import { type Command, CommandPalette } from "../command/CommandPalette";
import "./AppShell.css";
import { TrustStrip } from "./TrustStrip";

// North-star Decision Surfaces (01-north-star-architecture.md). Slots only in T3;
// each surface gets real content in later tasks.
const SURFACES = [
  "Rookie Board",
  "Roster Audit",
  "Trade Lab",
  "Waiver Radar",
  "League Pulse",
  "Backtest Harness",
  "Research Assistant",
] as const;

type Surface = (typeof SURFACES)[number];

export function AppShell() {
  const [activeSurface, setActiveSurface] = useState<Surface>(SURFACES[0]);
  const [inspectorOpen, setInspectorOpen] = useState(true);

  const commands: Command[] = SURFACES.map((surface) => ({
    id: surface.toLowerCase().replace(/\s+/g, "-"),
    label: surface,
    run: () => {
      setActiveSurface(surface);
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
            onClick={() => setActiveSurface(surface)}
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
        <h1 className="dg-shell__title">{activeSurface}</h1>
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
      </aside>

      <CommandPalette commands={commands} />
    </div>
  );
}
