// Surface-3 T7 — player inspector neutral preview.
//
// Fetches the typed PlayerDetailResponse and renders a NEUTRAL preview only:
// model status, market availability, and presence COUNTS (never grades, scores,
// deltas, raw evidence/caveat text, tiers, glyphs, or recommendations). Unmodeled
// categories are labelled explicitly. The full evidence card lives on T8's page.
import { useEffect, useState } from "react";
import type { z } from "zod";

import { zPlayerDetailResponse } from "../lib/api/zod.gen";

type PlayerDetail = z.infer<typeof zPlayerDetailResponse>;
type PreviewState =
  | { status: "loading" }
  | { status: "ready"; detail: PlayerDetail }
  | { status: "unavailable" };

function pluralize(count: number, singular: string, plural: string): string {
  return `${count} ${count === 1 ? singular : plural}`;
}

function NeutralPreview({ detail }: { detail: PlayerDetail }) {
  const modeled = detail.model_status === "modeled";
  const marketAvailable = detail.market?.status === "available";
  const evidence = detail.evidence;

  return (
    <div className="dg-player-inspector__preview">
      {modeled ? (
        <p className="dg-player-inspector__status">Modeled</p>
      ) : (
        <>
          <p className="dg-player-inspector__status">Unmodeled category</p>
          <p className="dg-player-inspector__status-note">No active model score</p>
        </>
      )}
      <p className="dg-player-inspector__market">
        {marketAvailable ? "Market available" : "Market unavailable"}
      </p>
      {evidence && (
        <>
          <p className="dg-player-inspector__counts">
            {pluralize(evidence.caveats.items.length, "caveat", "caveats")} ·{" "}
            {evidence.counter_argument.status === "available"
              ? "counter-argument available"
              : "counter-argument unavailable"}
          </p>
          <p className="dg-player-inspector__counts">
            {pluralize(evidence.top_drivers.items.length, "driver", "drivers")} ·{" "}
            {pluralize(evidence.risk_flags.items.length, "risk flag", "risk flags")}
          </p>
        </>
      )}
      <p className="dg-player-inspector__decision">Decision support only</p>
    </div>
  );
}

export function PlayerInspector({
  player,
  onClose,
}: {
  player: { sleeperId: string; label: string };
  onClose: () => void;
}) {
  const [preview, setPreview] = useState<PreviewState>({ status: "loading" });

  useEffect(() => {
    let active = true;
    setPreview({ status: "loading" });
    (async () => {
      try {
        const response = await fetch(`/api/players/${player.sleeperId}`);
        if (!response.ok) {
          if (active) setPreview({ status: "unavailable" });
          return;
        }
        const parsed = zPlayerDetailResponse.safeParse(await response.json());
        if (!active) return;
        setPreview(
          parsed.success
            ? { status: "ready", detail: parsed.data }
            : { status: "unavailable" },
        );
      } catch {
        if (active) setPreview({ status: "unavailable" });
      }
    })();
    return () => {
      active = false;
    };
  }, [player.sleeperId]);

  return (
    <div className="dg-player-inspector">
      <p className="dg-player-inspector__name">{player.label}</p>
      <p className="dg-player-inspector__id">{player.sleeperId}</p>
      {preview.status === "ready" && <NeutralPreview detail={preview.detail} />}
      {preview.status === "unavailable" && (
        <p className="dg-player-inspector__counts">Preview unavailable</p>
      )}
      <button type="button" className="dg-player-inspector__open">
        Open full evidence card
      </button>
      <button
        type="button"
        className="dg-player-inspector__close"
        aria-label="Close player inspector"
        onClick={onClose}
      >
        Close
      </button>
    </div>
  );
}
