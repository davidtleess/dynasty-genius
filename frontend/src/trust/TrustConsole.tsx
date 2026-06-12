// Model Trust Console — T5 data shell.
//
// Read-only. Per active position, fetches the trust-surface + curated model-card,
// validates each at the Zod boundary, and maps to the anti-leakage view-model. Honest
// degradation: an unavailable/invalid trust-surface degrades the whole shell; a missing
// model-card degrades INDEPENDENTLY. T6-T9 fill the panels from the view-model.
import { useEffect, useState } from "react";

import { zModelCardResponse, zTrustSurfaceResponse } from "../lib/api/zod.gen";
import { FoldTable } from "./FoldTable";
import { GateMatrix } from "./GateMatrix";
import "./TrustConsole.css";
import { TrustTruthPanel } from "./TrustTruthPanel";
import {
  buildTrustConsoleViewModel,
  type ModelCardData,
  type TrustConsoleViewModel,
} from "./trustViewModel";

const POSITIONS = ["QB", "RB", "WR", "TE"] as const;
type Position = (typeof POSITIONS)[number];

type ConsoleState =
  | { status: "loading" }
  | { status: "ready"; vm: TrustConsoleViewModel }
  | { status: "unavailable" };

export function TrustConsole() {
  const [activePosition, setActivePosition] = useState<Position>("QB");
  const [state, setState] = useState<ConsoleState>({ status: "loading" });

  useEffect(() => {
    let active = true;
    setState({ status: "loading" });
    (async () => {
      try {
        const surfaceResponse = await fetch(`/api/trust-surface/${activePosition}`);
        if (!surfaceResponse.ok) {
          if (active) setState({ status: "unavailable" });
          return;
        }
        // Validate at the Zod boundary; parse() throws on invalid -> outer catch -> unavailable.
        const surfaceData = zTrustSurfaceResponse.parse(await surfaceResponse.json());
        // Model-card degrades independently — never blanks the trust shell.
        let card: ModelCardData | null = null;
        try {
          const cardResponse = await fetch(
            `/api/trust-surface/${activePosition}/model-card`,
          );
          if (cardResponse.ok) {
            card = zModelCardResponse.parse(await cardResponse.json());
          }
        } catch {
          card = null;
        }
        if (!active) return;
        setState({
          status: "ready",
          vm: buildTrustConsoleViewModel(surfaceData, card),
        });
      } catch {
        if (active) setState({ status: "unavailable" });
      }
    })();
    return () => {
      active = false;
    };
  }, [activePosition]);

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

      {state.status === "loading" && (
        <p className="dg-trust-console__status">Loading trust data</p>
      )}
      {state.status === "unavailable" && (
        <p className="dg-trust-console__status">Trust data unavailable</p>
      )}
      {state.status === "ready" && (
        <div className="dg-trust-console__body">
          <p className="dg-trust-console__status">Trust data loaded</p>
          <TrustTruthPanel vm={state.vm} />
          <GateMatrix gates={state.vm.gates} />
          <FoldTable folds={state.vm.folds} />
          {state.vm.model_card === null && (
            <p className="dg-trust-console__degraded">Model card unavailable</p>
          )}
        </div>
      )}
    </div>
  );
}
