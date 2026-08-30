import type { z } from "zod";

import type { zTradeRosterReconciliation } from "../lib/api/zod.gen";
import { describeToken, VALUE_OVER_REPLACEMENT } from "../lib/copy";
import { PlayerNameButton } from "../player/playerSelection";
import { TokenNotes } from "../ui/TokenNotes";
import { RangeRow } from "./forcedCutRange";

type ModelReconciliation = z.infer<typeof zTradeRosterReconciliation>;

// Our model's side of the pricing (the blue lane). Renders the
// value-over-replacement side values under plain labels, the forced-cut
// capacity value-at-risk / recovery ranges (PR #92 net RC v1 ranges — the old
// gross scalar is a backend compatibility field and is never displayed), and
// the parity state in words. The backend's favors / adjusted_favors fields are
// intentionally NEVER read or rendered — a directional "favors" label is a
// banned binary verdict. These ranges are descriptive overlays
// (decision_supported=false).
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
      {/* DG-116 gives every lane a plain title plus a scale line, so a manager
          reads WHOSE price this is before reading what the numbers are in.
          DG-117 owns the name of the quantity itself: `VALUE_OVER_REPLACEMENT`
          is the ONE name for it, and its jargon rule flags every other
          spelling — so the scale line uses the constant rather than declaring a
          fifth phrasing of the same thing. */}
      <h3 className="dg-lane__title">Our model</h3>
      <p className="dg-lane__scale">{VALUE_OVER_REPLACEMENT}</p>
      <dl className="dg-lane__metrics">
        <dt>You send</dt>
        <dd>{evaluation.side_a.side_value}</dd>
        <dt>You get</dt>
        <dd>{evaluation.side_b.side_value}</dd>
        <dt>Close to even?</dt>
        <dd>
          {reconciliation.adjusted_within_parity_band
            ? "Yes, inside our even-trade band"
            : "No, outside our even-trade band"}
        </dd>
      </dl>

      {isBlocked ? (
        // WAS: "Roster rules conflict: transaction blocked." — which asserted
        // the league would reject the trade. The producer means no such thing.
        // `penalty_status = "blocked"` is set on exactly two paths, and both are
        // "we could not compute the cut's cost": a capacity audit that did not
        // return ok (reconciler.py:204-207), and a forced cut carrying no model
        // value, which "would silently UNDER-penalize if treated as 0, so it
        // blocks the net range as incomplete" (:222-223, :261-284). Nothing in
        // either path is a roster-rule violation.
        <p className="dg-forced-cut-blocked">
          We could not work out what the forced cut would cost, so that cost is left out
          of the numbers here.
        </p>
      ) : (
        <div className="dg-forced-cut-ranges">
          <RangeRow
            label="What the forced cut could cost you"
            range={penalty.forced_cut_value_at_risk_range}
          />
          <RangeRow
            label="What you could get back off waivers"
            range={penalty.forced_cut_recovery_range}
          />
          <RangeRow
            label="How far from even, once the cut is counted"
            range={reconciliation.adjusted_fairness_delta_range}
          />
          <RangeRow
            label="What their side is worth to you, once the cut is counted"
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
        <ul className="dg-lane__caveats" aria-label="Capacity notes">
          {penalty.penalty_caveats.map((caveat) => (
            <li key={caveat}>{describeToken(caveat)}</li>
          ))}
        </ul>
      )}

      {penalty.forced_cut_candidates.length > 0 && (
        <ul className="dg-lane__cuts" aria-label="Who you would have to cut">
          {penalty.forced_cut_candidates.map((cut, index) => {
            const sleeperId =
              typeof cut.sleeper_player_id === "string" ? cut.sleeper_player_id : null;
            const name =
              typeof cut.full_name === "string"
                ? cut.full_name
                : (sleeperId ?? `cut ${index + 1}`);
            // DG-110: a named cut candidate opens that player's card.
            return (
              <li key={name}>
                <PlayerNameButton sleeperId={sleeperId} name={name} />
              </li>
            );
          })}
        </ul>
      )}

      {/* Same DG-109 review fix as the market lane: this block was left raw. */}
      {reconciliation.caveats.length > 0 && (
        <TokenNotes className="dg-lane__caveats" tokens={reconciliation.caveats} />
      )}
    </section>
  );
}
