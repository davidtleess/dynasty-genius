import { useEffect, useState } from "react";
import type { RosterAuditResponse } from "../lib/api";
import { zRosterAuditResponse } from "../lib/api/zod.gen";
import { QbContextSection } from "./QbContextSection";
import "./RosterAudit.css";
import { type ControlsState, RosterAuditControls } from "./RosterAuditControls";
import { RosterAuditHeader } from "./RosterAuditHeader";
import {
  ConfigErrorState,
  EmptyState,
  LoadingState,
  ParseErrorState,
  UnavailableState,
} from "./RosterAuditStates";
import { RosterAuditTable } from "./RosterAuditTable";
import { applyFilter, applyGroup, type Player } from "./rosterTransform";

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
  const allPlayers = data.players ?? [];
  const cards = data.qb_context_cards ?? [];
  const caveats = data.caveats ?? [];

  return (
    <ReadyView data={data} allPlayers={allPlayers} cards={cards} caveats={caveats} />
  );
}

// Success-state view: owns the local sort/filter/group UI state and runs the
// pure transform over the players before rendering. Default state (none/all)
// is identity-preserving, so the surface still renders the backend order.
function ReadyView({
  data,
  allPlayers,
  cards,
  caveats,
}: {
  data: RosterAuditResponse;
  allPlayers: Player[];
  cards: NonNullable<RosterAuditResponse["qb_context_cards"]>;
  caveats: string[];
}) {
  const [ctrl, setCtrl] = useState<ControlsState>({
    sortKey: "none",
    groupBy: "none",
    positions: [],
    prospect: "all",
  });
  const allPositions = Array.from(new Set(allPlayers.map((p) => p.position)));
  const filtered = applyFilter(allPlayers, {
    positions: ctrl.positions,
    prospect: ctrl.prospect,
  });
  const groups = applyGroup(filtered, ctrl.groupBy, ctrl.sortKey);
  const filteredOutCount = allPlayers.length - filtered.length;
  const reset = () =>
    setCtrl({ sortKey: "none", groupBy: "none", positions: [], prospect: "all" });

  return (
    <div className="dg-roster">
      <RosterAuditHeader
        status={data.status}
        modelStatusByPosition={data.model_status_by_position ?? {}}
        caveats={caveats}
        droppedPlayerCount={data.dropped_player_count ?? 0}
      />
      {allPlayers.length === 0 ? (
        <EmptyState />
      ) : (
        <>
          <RosterAuditControls
            {...ctrl}
            allPositions={allPositions}
            filteredOutCount={filteredOutCount}
            onChange={setCtrl}
            onReset={reset}
          />
          {filtered.length === 0 ? (
            <p className="dg-roster__no-match" role="status">
              No rows match the current filters.{" "}
              <button type="button" onClick={reset}>
                Reset
              </button>
            </p>
          ) : (
            <RosterAuditTable groups={groups} />
          )}
        </>
      )}
      <QbContextSection cards={cards} />
    </div>
  );
}
