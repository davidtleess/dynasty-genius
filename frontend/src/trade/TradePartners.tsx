// DG-114 — partner rankings become the second view of Trades (spec §4.1:
// "Trades | Trade Lab + League Pulse 'Partner Rankings'").
//
// The panel itself is unchanged: same component, same fields, same honesty note
// about the score being partly market-derived. What changed is WHERE it lives.
// Who to call about a trade is a trade question, and it sat two rail items away
// from the trade builder, three quarters of the way down a 46-screen page.
//
// It reads the same endpoint League Pulse reads, and it degrades the same way:
// a failed read says it failed rather than rendering an empty ranking, which
// would read as "you have no good trade partners".
import { useEffect, useState } from "react";

import type { LeaguePulseResponse } from "../lib/api";
import { zLeaguePulseResponse } from "../lib/api/zod.gen";
import "../league-pulse/LeaguePulse.css";
import { PartnerRankings } from "../league-pulse/PartnerRankings";
import { PostureBasis } from "../league-pulse/PostureBasis";

type State =
  | { status: "loading" }
  | { status: "ready"; data: LeaguePulseResponse }
  | { status: "unavailable" }
  | { status: "parse-error" };

export function TradePartners() {
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    let active = true;
    setState({ status: "loading" });
    (async () => {
      try {
        const res = await fetch("/api/league/pulse");
        if (!res.ok) {
          if (active) setState({ status: "unavailable" });
          return;
        }
        const data = zLeaguePulseResponse.parse(
          await res.json(),
        ) as LeaguePulseResponse;
        if (active) setState({ status: "ready", data });
      } catch {
        if (active) setState({ status: "parse-error" });
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  if (state.status === "loading") {
    return <p className="dg-league-pulse__state">Loading trade partners…</p>;
  }
  if (state.status === "unavailable") {
    return (
      <p className="dg-league-pulse__state">
        Trade partners unavailable. The league snapshot could not be loaded right now.
      </p>
    );
  }
  if (state.status === "parse-error") {
    return (
      <p className="dg-league-pulse__state">
        Could not read the league snapshot. The response was not in the expected shape.
      </p>
    );
  }
  // The posture disclosure travels WITH the cards. Each card prints the two
  // posture words the paragraph explains, and a posture word with no basis
  // above it is a claim about a manager's intent that nobody can back.
  return (
    <>
      <PostureBasis />
      <PartnerRankings rankings={state.data.partner_rankings ?? []} />
    </>
  );
}
