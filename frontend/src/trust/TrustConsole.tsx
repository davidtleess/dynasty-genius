// Model Trust Console — T4 minimal placeholder.
//
// Read-only surface. v1 renders per-position trust legibility (truth panel, gate
// matrix, fold table, model-card essentials, provenance). T4 is just the shell:
// the position controls. T5 fills it (view-model + fetch + sections). The shell's
// title heading supplies "Model Trust"; this component renders the position tabs.
import { useState } from "react";

const POSITIONS = ["QB", "RB", "WR", "TE"] as const;
type Position = (typeof POSITIONS)[number];

export function TrustConsole() {
  const [activePosition, setActivePosition] = useState<Position>("QB");

  return (
    <div className="dg-trust-console">
      <div className="dg-trust-console__tabs">
        {POSITIONS.map((position) => (
          <button
            key={position}
            type="button"
            className="dg-trust-console__tab"
            aria-pressed={activePosition === position}
            onClick={() => setActivePosition(position)}
          >
            {position}
          </button>
        ))}
      </div>
    </div>
  );
}
