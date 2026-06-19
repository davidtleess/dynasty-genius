import type { RosterAuditResponse } from "../lib/api";

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
      <div className="dg-roster__status" data-status={status}>
        Status: <strong>{status}</strong>
      </div>
      <p className="dg-roster__disclaimer">Experimental — not decision-grade.</p>
      <ul className="dg-roster__model-status">
        {Object.entries(modelStatusByPosition).map(([pos, st]) => (
          <li key={pos} className="dg-roster__chip" data-status={st}>
            <span>{pos}</span> <span>{st}</span>
          </li>
        ))}
      </ul>
      {droppedPlayerCount > 0 && (
        <p className="dg-roster__dropped">
          {droppedPlayerCount} row(s) dropped (corrupt/unmappable).
        </p>
      )}
      {caveats.length > 0 && (
        <ul className="dg-roster__caveats">
          {caveats.map((c) => (
            <li key={c}>{c}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
