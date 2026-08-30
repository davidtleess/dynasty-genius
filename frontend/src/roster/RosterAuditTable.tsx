import type { RosterAuditResponse } from "../lib/api";
import { fieldLabel } from "../lib/copy";
import { TableScroll } from "../ui/TableScroll";
import { RosterAuditRow } from "./RosterAuditRow";
import type { RosterGroup } from "./rosterTransform";

// Neutral, descriptive column labels only — no verdict vocabulary.
//
// DG-117 removed a tenth column. `model_status_applies` is the single
// expression `engine_used == "engine_b"` (roster_audit_models.py:264), rendered
// as "applies" / "n/a" — and on David's live roster it was "n/a" on all 27
// rows, because not one of his players is scored by the active-player model.
// Where it does vary it MISLEADS: the four players who are scored are scored by
// the ROOKIE model, and this column told him "n/a" about them too, next to a
// Model status cell that says "Scored by the rookie model — accuracy grade C".
// The column carried no fact its neighbour does not carry better, so it goes.
//
// The neighbour is now named by the dictionary rather than by hand: `fieldLabel`
// calls `model_grade` "Model status", which is what the player card calls the
// same field. One field, one name, both places.
const COLUMNS = [
  "Player",
  "Pos",
  "Team",
  "Age",
  // DG-109: was "DVS". Three capitals slipped under the render rule's four-capital
  // floor, but it is machinery either way — the dictionary already calls this
  // field "Dynasty value" everywhere else.
  fieldLabel("model_grade"),
  fieldLabel("dynasty_value_score"),
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

  // DG-117 — the blank cells get one sentence, under the table, once.
  //
  // 23 of David's 27 rows read "Not scored yet / n/a / —" and nothing on the
  // surface said why an em dash was an em dash. It is counted from the rows
  // actually rendered (so it stays true under a filter), and it claims exactly
  // what a dash in that column means and no more: there is no score, we are not
  // guessing one, and the row's own Details panel carries the producer's reason
  // for that player. Inventing a shared cause here — "the model has not been
  // validated for their position" — would be a claim this component cannot see
  // and cannot check.
  const rendered = groups.flatMap((g) => g.players);
  const unscored = rendered.filter((p) => p.dynasty_value_score == null).length;

  return (
    <>
      <TableScroll label="Roster audit table">
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
      </TableScroll>
      {unscored > 0 && (
        <p className="dg-roster__unscored-note">
          {/* The sentence names the column by the column's own name. An earlier
              draft said "no value score", which is a sixth name for a field the
              header calls "Dynasty value" — the exact drift this ticket exists
              to close, committed inside the fix for it. */}
          {unscored} of these {rendered.length} players have no{" "}
          {fieldLabel("dynasty_value_score").toLowerCase()} yet, so those cells are left
          blank rather than guessed. Open Details on a row to see what is missing for
          that player.
        </p>
      )}
    </>
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
