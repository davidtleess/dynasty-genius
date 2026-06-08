// Surface-3 T8 — the player detail page. Fetches the typed PlayerDetailResponse,
// validates at the Zod boundary, and renders the full Decision-Evidence-Card or a
// degraded state (honest degradation, never a raw or fabricated card).
import { useEffect, useState } from "react";
import type { z } from "zod";

import { zPlayerDetailResponse } from "../lib/api/zod.gen";
import { PlayerDetailCard } from "./PlayerDetailCard";

type PlayerDetail = z.infer<typeof zPlayerDetailResponse>;
type PageState =
  | { status: "loading" }
  | { status: "ready"; detail: PlayerDetail }
  | { status: "unavailable" };

export function PlayerDetailPage({ sleeperId }: { sleeperId: string }) {
  const [state, setState] = useState<PageState>({ status: "loading" });

  useEffect(() => {
    let active = true;
    setState({ status: "loading" });
    (async () => {
      try {
        const response = await fetch(`/api/players/${sleeperId}`);
        if (!response.ok) {
          if (active) setState({ status: "unavailable" });
          return;
        }
        const parsed = zPlayerDetailResponse.safeParse(await response.json());
        if (!active) return;
        setState(
          parsed.success
            ? { status: "ready", detail: parsed.data }
            : { status: "unavailable" },
        );
      } catch {
        if (active) setState({ status: "unavailable" });
      }
    })();
    return () => {
      active = false;
    };
  }, [sleeperId]);

  if (state.status === "loading") {
    return <p className="dg-player-detail__loading">Loading player detail…</p>;
  }
  if (state.status === "unavailable") {
    return <p className="dg-player-detail__loading">Player detail unavailable.</p>;
  }
  return <PlayerDetailCard detail={state.detail} />;
}
