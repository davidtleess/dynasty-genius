import { useEffect, useState } from "react";

import type { RosterCapacityResponse } from "../lib/api/types.gen";
import { zRosterCapacityResponse } from "../lib/api/zod.gen";
import { describeStatusToken } from "../lib/copy";
import "./RosterCapacitySandbox.css";

type State =
  | { status: "loading" }
  | { status: "ready"; data: RosterCapacityResponse }
  | { status: "unavailable" }
  | { status: "parse-error" };

// Read-only Roster Capacity sandbox: manual fetch + generated Zod parse (no
// callable client). Descriptive only — it renders capacity facts and value-at-risk
// RANGES so David can test cut hypotheses; it issues no verdict, nominates no
// target, and never collapses a range into a single point estimate.
export function RosterCapacitySandbox() {
  const [state, setState] = useState<State>({ status: "loading" });

  useEffect(() => {
    let active = true;
    setState({ status: "loading" });
    (async () => {
      try {
        const res = await fetch("/api/roster/capacity");
        if (!res.ok) {
          if (active) setState({ status: "unavailable" });
          return;
        }
        const data = zRosterCapacityResponse.parse(
          await res.json(),
        ) as RosterCapacityResponse;
        if (active) setState({ status: "ready", data });
      } catch {
        if (active) setState({ status: "parse-error" });
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  if (state.status === "loading") {
    return <p className="dg-rc__notice">Loading roster capacity…</p>;
  }
  if (state.status === "unavailable") {
    return <p className="dg-rc__notice">Roster capacity unavailable.</p>;
  }
  if (state.status === "parse-error") {
    return <p className="dg-rc__notice">Could not read roster capacity.</p>;
  }

  return <ReadyView data={state.data} />;
}

// A range is rendered as an explicit low→high span (never a midpoint/average),
// with signed, unclamped values so a net-upgrade cut honestly reads negative.
function fmt(value: number): string {
  // Object.is distinguishes -0 from 0; toFixed collapses -0 to "0.00", which
  // would silently drop the sign of a boundary value (a signed 0 can survive
  // JSON parsing) and break the signed-range display contract.
  if (Object.is(value, -0)) {
    return "-0.00";
  }
  return value.toFixed(2);
}

function RangeSpan({
  kind,
  bounds,
}: {
  kind: string;
  bounds: number[] | null | undefined;
}) {
  const low = bounds?.[0];
  const high = bounds?.[1];
  if (low === undefined || high === undefined) {
    return <span className="dg-rc__range-unavailable">range unavailable</span>;
  }
  return (
    <span className="dg-rc__range" data-range-kind={kind}>
      {fmt(low)} to {fmt(high)}
    </span>
  );
}

function ReadyView({ data }: { data: RosterCapacityResponse }) {
  const blocked = data.artifact_status === "blocked" || data.status === "blocked";

  // One consolidated, de-duplicated notices panel: the same caveat can surface
  // both at the top level and under a position pool; showing it once keeps the
  // panel honest without implying two independent problems.
  const pools = data.unrostered_pool_range ?? {};
  const caveats = Array.from(
    new Set([
      ...(data.caveats ?? []),
      ...Object.values(pools).flatMap((pool) => pool?.caveats ?? []),
    ]),
  );

  return (
    <section className="dg-rc" aria-label="Roster Capacity Sandbox">
      <p className="dg-rc__disclaimer">Descriptive only — not decision-grade.</p>
      <p className="dg-rc__disclaimer">
        Capacity facts and value-at-risk ranges; no verdict, no nominated cut.
      </p>
      <p className="dg-rc__status">Artifact status: {data.artifact_status}</p>

      {caveats.length > 0 && (
        <ul className="dg-rc__caveats" aria-label="Caveats">
          {caveats.map((caveat) => (
            <li key={caveat} className="dg-rc__caveat">
              {describeStatusToken(caveat)}
            </li>
          ))}
        </ul>
      )}

      {blocked ? (
        <p className="dg-rc__blocked">
          No capacity numbers are shown for a blocked artifact.
        </p>
      ) : (
        <>
          {data.capacity_health && (
            <dl className="dg-rc__health">
              <div>
                <dt>Total capacity cuts required</dt>
                <dd>{data.capacity_health.total_capacity_cuts_required}</dd>
              </div>
              <div>
                <dt>Active slot overflow</dt>
                <dd>{data.capacity_health.active_slot_overflow}</dd>
              </div>
            </dl>
          )}

          <p className="dg-rc__sort-basis">
            Candidates sorted by cut exposure rank as diagnostic order — not a cut
            sequence.
          </p>

          {(data.candidates ?? []).length === 0 ? (
            <p className="dg-rc__empty">No capacity candidates.</p>
          ) : (
            <table className="dg-rc__table">
              <thead>
                <tr className="dg-rc__row">
                  <th scope="col">Player</th>
                  <th scope="col">Pos</th>
                  <th scope="col">Cut exposure rank</th>
                  <th scope="col">xVAR</th>
                </tr>
              </thead>
              <tbody>
                {(data.candidates ?? []).map((c) => (
                  <tr key={c.sleeper_player_id} className="dg-rc__row">
                    <td>{c.full_name}</td>
                    <td>{c.position}</td>
                    <td>{c.cut_priority}</td>
                    <td>
                      {c.raw_xvar === null || c.raw_xvar === undefined
                        ? "unavailable"
                        : fmt(c.raw_xvar)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {(data.scenarios ?? []).map((scenario, index) => (
            <div
              className="dg-rc__scenario"
              key={scenario.cut_set?.join("+") || `scenario-${index}`}
            >
              <p>
                Cumulative value-at-risk:{" "}
                <RangeSpan
                  kind="cumulative_value_at_risk"
                  bounds={scenario.cumulative_value_at_risk}
                />
              </p>
              <p>
                Marginal next candidate cost:{" "}
                {scenario.marginal_next_candidate_cost ? (
                  <RangeSpan
                    kind="marginal_next_candidate_cost"
                    bounds={scenario.marginal_next_candidate_cost}
                  />
                ) : (
                  <span className="dg-rc__range-unavailable">unavailable</span>
                )}
              </p>
            </div>
          ))}

          <ul className="dg-rc__pools" aria-label="Waiver replacement ranges">
            {Object.entries(pools).map(([position, pool]) => (
              <li key={position} className="dg-rc__pool">
                {pool &&
                pool.status === "ok" &&
                pool.low !== null &&
                pool.high !== null ? (
                  <>
                    {position}:{" "}
                    <RangeSpan
                      kind="unrostered_pool_range"
                      bounds={[pool.low, pool.high]}
                    />
                  </>
                ) : (
                  <>{position} range unavailable</>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
