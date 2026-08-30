import type { RosterAuditResponse } from "../lib/api";
import { positionTrustWord, valueWord } from "../lib/copy";
import { TokenNotes } from "../ui/TokenNotes";

type Props = {
  status: RosterAuditResponse["status"];
  modelStatusByPosition: NonNullable<RosterAuditResponse["model_status_by_position"]>;
  caveats: string[];
  droppedPlayerCount: number;
};

// Honesty header: overall status, per-position model_status chips, dropped-row
// count, envelope caveats, and the surface expression of decision_supported=False.
export function RosterAuditHeader({
  status,
  modelStatusByPosition,
  caveats,
  droppedPlayerCount,
}: Props) {
  return (
    <section className="dg-roster__header" aria-label="Roster audit status">
      {/* DG-109: the envelope status and the per-position trust chips printed
          their own enums (`active`, `VALIDATED`, `PROVISIONAL`). The state each
          one reports is unchanged and still rides `data-status` for CSS and
          tests; only the word a person reads changed. The chips get their OWN
          vocabulary — `EXPERIMENTAL` here means the position's validation record
          is missing or stale (roster_audit_models.py:55-76), which is not what
          the same word means on a player's model grade. */}
      <div className="dg-roster__status" data-status={status}>
        Status: <strong>{valueWord(status)}</strong>
      </div>
      <p className="dg-roster__disclaimer">Experimental — not decision-grade.</p>
      <ul className="dg-roster__model-status">
        {Object.entries(modelStatusByPosition).map(([pos, st]) => (
          <li key={pos} className="dg-roster__chip" data-status={st}>
            <span>{pos}</span> <span>{positionTrustWord(st)}</span>
          </li>
        ))}
      </ul>
      {droppedPlayerCount > 0 && (
        <p className="dg-roster__dropped">
          {droppedPlayerCount} row(s) dropped (corrupt/unmappable).
        </p>
      )}
      {caveats.length > 0 && (
        <TokenNotes className="dg-roster__caveats" tokens={caveats} />
      )}
    </section>
  );
}
