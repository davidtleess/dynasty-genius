import type { RosterAuditResponse } from "../lib/api";
import { positionTrustWord } from "../lib/copy";
import { TokenNotes } from "../ui/TokenNotes";

type Props = {
  status: RosterAuditResponse["status"];
  modelStatusByPosition: NonNullable<RosterAuditResponse["model_status_by_position"]>;
  caveats: string[];
  droppedPlayerCount: number;
};

// Honesty header: overall status, per-position model_status chips, dropped-row
// count and envelope caveats.
export function RosterAuditHeader({
  status,
  modelStatusByPosition,
  caveats,
  droppedPlayerCount,
}: Props) {
  return (
    <section className="dg-roster__header" aria-label="Roster audit status">
      {/* DG-111: the "Status: ok" chip and the "Experimental — not
          decision-grade." stamp are retired. `status` is the closed union
          'active' | 'degraded' (types.gen.ts RosterAuditResponse), so this is
          exhaustive over the non-healthy case and no state is swallowed: when it
          is degraded the fact is said out loud, which is the only time the chip
          ever told David anything.

          The element itself is conditional, not just its text. Nothing styles or
          queries `.dg-roster__status` on a HEALTHY read (grep: this file only —
          RosterAudit.css carries no rule for it), so rendering it empty would
          ship a hollow div; the one reader is RosterAuditHeader.test.jsx, which
          looks for [data-status="degraded"], and that attribute is right here on
          the branch it asks about. */}
      {status === "degraded" ? (
        <div className="dg-roster__status" data-status={status}>
          <span>
            Heads up: this roster read came back degraded — treat the numbers below as
            provisional.
          </span>
        </div>
      ) : null}
      {/* DG-109: the per-position trust chips printed their own enums
          (`VALIDATED`, `PROVISIONAL`, `EXPERIMENTAL`). The state each one reports
          is unchanged and still rides `data-status` for CSS and tests; only the
          word a person reads changed. The chips get their OWN vocabulary —
          `EXPERIMENTAL` here means the position's validation record is missing or
          stale (roster_audit_models.py:55-76), which is not what the same word
          means on a player's model grade. */}
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
