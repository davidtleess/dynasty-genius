import type { RosterAuditResponse } from "../lib/api";
import { RosterAuditRow } from "./RosterAuditRow";
import type { RosterGroup } from "./rosterTransform";

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

type Player = NonNullable<RosterAuditResponse["players"]>[number];

export function RosterAuditTable(
  props: { players: Player[] } | { groups: RosterGroup[] },
) {
  // Flat view wraps players in a single unlabeled group; the empty label
  // suppresses the heading row, so flat rendering is byte-identical to Inc2.
  const groups: RosterGroup[] =
    "groups" in props
      ? props.groups
      : [{ key: "__all__", label: "", players: props.players }];

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
        {groups.map((g) => (
          <GroupBlock key={g.key} group={g} />
        ))}
      </tbody>
    </table>
  );
}

function GroupBlock({ group }: { group: RosterGroup }) {
  return (
    <>
      {group.label !== "" && (
        <tr className="dg-roster__group-heading">
          <th colSpan={COLUMNS.length} scope="rowgroup">
            {group.label}
          </th>
        </tr>
      )}
      {group.players.map((p) => (
        <RosterAuditRow key={p.player_id} player={p} />
      ))}
    </>
  );
}
