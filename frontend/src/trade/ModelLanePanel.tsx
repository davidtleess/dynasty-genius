import type { z } from "zod";

import type { zTradeRosterReconciliation } from "../lib/api/zod.gen";

type ModelReconciliation = z.infer<typeof zTradeRosterReconciliation>;

// Model View (blue lane). Renders the xVAR side values, the forced-cut
// penalty, and the parity state. The backend's favors / adjusted_favors
// fields are intentionally NEVER read or rendered — a directional "favors"
// label is a banned binary verdict.
export function ModelLanePanel({
  reconciliation,
}: {
  reconciliation: ModelReconciliation;
}) {
  const evaluation = reconciliation.base_evaluation;
  const penalty = reconciliation.roster_penalty;

  return (
    <section
      className="dg-lane dg-lane--model"
      data-lane="model"
      data-testid="model-lane"
    >
      <h3 className="dg-lane__title">Model view (xVAR)</h3>
      <dl className="dg-lane__metrics">
        <dt>Sent</dt>
        <dd>{evaluation.side_a.side_value}</dd>
        <dt>Received</dt>
        <dd>{evaluation.side_b.side_value}</dd>
        <dt>Forced-cut penalty</dt>
        <dd>{penalty.forced_cut_penalty_xvar}</dd>
        <dt>Parity</dt>
        <dd>
          {reconciliation.adjusted_within_parity_band ? "within band" : "outside band"}
        </dd>
      </dl>
      {penalty.forced_cut_candidates.length > 0 && (
        <ul className="dg-lane__cuts" aria-label="Forced cut candidates">
          {penalty.forced_cut_candidates.map((cut, index) => {
            const name =
              typeof cut.full_name === "string"
                ? cut.full_name
                : typeof cut.sleeper_player_id === "string"
                  ? cut.sleeper_player_id
                  : `cut ${index + 1}`;
            return <li key={name}>{name}</li>;
          })}
        </ul>
      )}
      {reconciliation.caveats.length > 0 && (
        <ul className="dg-lane__caveats">
          {reconciliation.caveats.map((caveat) => (
            <li key={caveat}>{caveat}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
