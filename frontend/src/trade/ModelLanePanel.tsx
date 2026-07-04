import type { z } from "zod";

import type { zTradeRosterReconciliation } from "../lib/api/zod.gen";
import { humanizeToken, RangeRow } from "./forcedCutRange";

type ModelReconciliation = z.infer<typeof zTradeRosterReconciliation>;

// Model View (blue lane). Renders the xVAR side values, the forced-cut capacity
// value-at-risk / recovery ranges (PR #92 net RC v1 ranges — the old gross
// scalar is a backend compatibility field and is never displayed), and the
// parity state. The backend's favors / adjusted_favors fields are intentionally
// NEVER read or rendered — a directional "favors" label is a banned binary
// verdict. These ranges are descriptive overlays (decision_supported=false).
export function ModelLanePanel({
  reconciliation,
}: {
  reconciliation: ModelReconciliation;
}) {
  const evaluation = reconciliation.base_evaluation;
  const penalty = reconciliation.roster_penalty;
  const isBlocked = penalty.penalty_status === "blocked";
  const isPoolUnavailable = penalty.penalty_status === "uncertain_pool_unavailable";

  return (
    <section
      className="dg-lane dg-lane--model"
      data-lane="model"
      data-testid="model-lane"
      data-visual-weight="equal"
    >
      <h3 className="dg-lane__title">Model view (xVAR)</h3>
      <dl className="dg-lane__metrics">
        <dt>Sent</dt>
        <dd>{evaluation.side_a.side_value}</dd>
        <dt>Received</dt>
        <dd>{evaluation.side_b.side_value}</dd>
        <dt>Parity</dt>
        <dd>
          {reconciliation.adjusted_within_parity_band ? "within band" : "outside band"}
        </dd>
      </dl>

      {isBlocked ? (
        <p className="dg-forced-cut-blocked">
          Roster rules conflict: transaction blocked.
        </p>
      ) : (
        <div className="dg-forced-cut-ranges">
          <RangeRow
            label="Value-at-risk range"
            range={penalty.forced_cut_value_at_risk_range}
          />
          <RangeRow label="Recovery range" range={penalty.forced_cut_recovery_range} />
          <RangeRow
            label="Adjusted fairness delta range"
            range={reconciliation.adjusted_fairness_delta_range}
          />
          <RangeRow
            label="Adjusted received value range"
            range={reconciliation.adjusted_received_value_range}
          />
        </div>
      )}

      {isPoolUnavailable && (
        <p className="dg-forced-cut-caveat">
          Waiver pool data stale — showing the widest possible range.
        </p>
      )}

      {penalty.penalty_caveats.length > 0 && (
        <ul className="dg-lane__caveats" aria-label="Penalty caveats">
          {penalty.penalty_caveats.map((caveat) => (
            <li key={caveat}>{humanizeToken(caveat)}</li>
          ))}
        </ul>
      )}

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
