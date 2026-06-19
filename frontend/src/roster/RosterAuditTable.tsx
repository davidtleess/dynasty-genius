import type { RosterAuditResponse } from "../lib/api";
import { RosterAuditRow } from "./RosterAuditRow";

// Neutral, descriptive column labels only — no verdict vocabulary.
const COLUMNS = [
  "Player",
  "Pos",
  "Team",
  "Age",
  "Model grade",
  "Model status",
  "DVS",
  "Age signal",
  "Signal completeness",
  "Caveats",
];

export function RosterAuditTable({
  players,
}: {
  players: NonNullable<RosterAuditResponse["players"]>;
}) {
  return (
    <table className="dg-roster__table">
      <thead>
        <tr>
          {COLUMNS.map((c) => (
            <th key={c}>{c}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {players.map((p) => (
          <RosterAuditRow key={p.player_id} player={p} />
        ))}
      </tbody>
    </table>
  );
}
