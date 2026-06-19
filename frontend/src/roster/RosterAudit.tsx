import { useEffect, useState } from "react";
import type { RosterAuditResponse } from "../lib/api";
import { zRosterAuditResponse } from "../lib/api/zod.gen";
import { QbContextSection } from "./QbContextSection";
import "./RosterAudit.css";
import { RosterAuditHeader } from "./RosterAuditHeader";
import {
  ConfigErrorState,
  EmptyState,
  LoadingState,
  ParseErrorState,
  UnavailableState,
} from "./RosterAuditStates";
import { RosterAuditTable } from "./RosterAuditTable";

type State =
  | { status: "loading" }
  | { status: "ready"; data: RosterAuditResponse }
  | { status: "config-error" }
  | { status: "unavailable" }
  | { status: "parse-error" };

// Read-only Roster Audit container: manual fetch + generated Zod parse (no callable
// client), mapping the contract into an honest state machine. 422 -> config-error,
// any other non-OK -> unavailable, parse failure -> parse-error. status="degraded"
// stays in the table view (the header renders its degraded banner).
export function RosterAudit() {
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    let active = true;
    setState({ status: "loading" });
    (async () => {
      try {
        const res = await fetch("/api/roster/audit");
        if (!res.ok) {
          if (active) {
            setState({ status: res.status === 422 ? "config-error" : "unavailable" });
          }
          return;
        }
        // Runtime-validated by Zod; cast reconciles the Zod-inferred optionality
        // representation with the generated RosterAuditResponse type.
        const data = zRosterAuditResponse.parse(
          await res.json(),
        ) as RosterAuditResponse;
        if (active) setState({ status: "ready", data });
      } catch {
        if (active) setState({ status: "parse-error" });
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  if (state.status === "loading") return <LoadingState />;
  if (state.status === "config-error") return <ConfigErrorState />;
  if (state.status === "unavailable") return <UnavailableState />;
  if (state.status === "parse-error") return <ParseErrorState />;

  const { data } = state;
  const players = data.players ?? [];
  const cards = data.qb_context_cards ?? [];
  const caveats = data.caveats ?? [];

  return (
    <div className="dg-roster">
      <RosterAuditHeader
        status={data.status}
        modelStatusByPosition={data.model_status_by_position ?? {}}
        caveats={caveats}
        droppedPlayerCount={data.dropped_player_count ?? 0}
      />
      {players.length === 0 ? <EmptyState /> : <RosterAuditTable players={players} />}
      <QbContextSection cards={cards} />
    </div>
  );
}
