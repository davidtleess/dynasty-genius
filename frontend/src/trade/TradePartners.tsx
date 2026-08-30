// DG-114 — partner rankings become the second view of Trades (spec §4.1:
// "Trades | Trade Lab + League Pulse 'Partner Rankings'").
//
// The panel itself is unchanged: same component, same fields, same honesty note
// about the score being partly market-derived. What changed is WHERE it lives.
// Who to call about a trade is a trade question, and it sat two rail items away
// from the trade builder, three quarters of the way down a 46-screen page.
//
// EVERY DISCLOSURE THE PANEL DEPENDED ON TRAVELS WITH IT. On League Pulse the
// cards stood under a header that printed four producer-emitted facts, and the
// first cut of this ticket carried only one of them (the posture basis). The
// review caught it. All four are here now:
//   · the capture time and the artifact-state sentence (SnapshotStamp),
//   · the partner records the assembler could not match (below),
//   · the schema version of the artifact these cards were built from,
//   · the posture basis (PostureBasis).
// A panel is only as honest as the facts standing next to it, and none of those
// facts is a property of the ADDRESS it used to have.
import { useEffect, useState } from "react";

import type { LeaguePulseResponse } from "../lib/api";
import { zLeaguePulseResponse } from "../lib/api/zod.gen";
import { receiptLine } from "../lib/copy";
import "../league-pulse/LeaguePulse.css";
import { PartnerRankings } from "../league-pulse/PartnerRankings";
import { PostureBasis } from "../league-pulse/PostureBasis";
import { SnapshotStamp } from "../league-pulse/SnapshotStamp";

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
      // Two try blocks, not one. A rejected fetch (offline, connection reset)
      // means NO RESPONSE ARRIVED; a thrown json()/parse means one arrived and
      // we could not read it. Catching both in one place made a network failure
      // print "The response was not in the expected shape." — a claim about a
      // response nobody received.
      let body: unknown;
      try {
        const res = await fetch("/api/league/pulse");
        if (!res.ok) {
          if (active) setState({ status: "unavailable" });
          return;
        }
        body = await res.json();
      } catch {
        if (active) setState({ status: "unavailable" });
        return;
      }
      try {
        const data = zLeaguePulseResponse.parse(body) as LeaguePulseResponse;
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

  // `dropped.partner_rankings` is the drop counter for THIS panel and nothing
  // else: the assembler increments it when a ranking's counterparty roster is
  // outside the snapshot, or when the record fails to map
  // (league_pulse_assembler.py:273-280). Without this line a list with two
  // partners missing reads as a complete list, and a list with ALL of them
  // missing reads as "you have no good trade partners" — absence stated where
  // only a failure happened, which is the defect the DG-110 panel was about.
  const withheld = state.data.dropped.partner_rankings ?? 0;
  // These cards, their fit scores and the posture words inside them all come
  // out of ONE artifact — the assembler reads partner_rankings from
  // `opportunity_artifact` (:272-280). So this page cites that artifact and no
  // other; naming the posture artifact here would credit a source these values
  // did not come from.
  const opportunityVersion = String(
    state.data.source_artifacts.league_opportunity.schema_version ?? "",
  );

  return (
    <section className="dg-league-pulse" aria-label="Trade partners">
      <SnapshotStamp capturedAt={state.data.captured_at} caveats={state.data.caveats} />
      {withheld > 0 ? (
        <p className="dg-league-pulse__withheld">
          {withheld === 1
            ? "1 partner record could not be matched up and is not shown below."
            : `${withheld} partner records could not be matched up and are not shown below.`}
        </p>
      ) : null}
      <ul className="dg-league-pulse__sources" data-receipt>
        <li>{receiptLine("League opportunity data", opportunityVersion)}</li>
      </ul>
      {/* The posture disclosure travels WITH the cards. Each card prints the two
          posture words the paragraph explains, and a posture word with no basis
          above it is a claim about a manager's intent that nobody can back. */}
      <PostureBasis />
      <PartnerRankings rankings={state.data.partner_rankings ?? []} />
    </section>
  );
}
