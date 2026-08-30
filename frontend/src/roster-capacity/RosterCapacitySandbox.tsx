import { useEffect, useState } from "react";

import type { RosterCapacityResponse } from "../lib/api/types.gen";
import { zRosterCapacityResponse } from "../lib/api/zod.gen";
import { describeToken, fieldLabel } from "../lib/copy";
import { PlayerNameButton } from "../player/playerSelection";
import { TableScroll } from "../ui/TableScroll";
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
      {/* DG-111: two stamps became one sentence that says what the surface is.
          The "no verdict, no nominated cut" clause stated the register David
          repealed; what it usefully meant — this shows the squeeze, it does not
          pick the man — survives in plain words. The raw artifact status only
          speaks when it is not clean. */}
      <p className="dg-rc__disclaimer">
        Where your roster is tight, and what each cut would cost you.
      </p>
      {/* REVIEW-PANEL FIX: this fired for EVERY non-ok status including
          `blocked`, and told the reader to treat "the ranges below" as
          provisional on the one path where there are no ranges below at all —
          the blocked branch renders no health block, no table and no scenario
          ranges. "Provisional" also softens "blocked": provisional means
          tentative, blocked means nothing is shown. Blocked gets its own line
          further down; this one now speaks only where there IS something below
          to qualify. The element itself is conditional, so a clean read does not
          ship an empty styled paragraph. */}
      {data.artifact_status === "degraded" && !blocked && (
        <p className="dg-rc__status" data-artifact-status={data.artifact_status}>
          Heads up: this capacity read came back degraded, so treat the ranges below as
          provisional.
        </p>
      )}

      {caveats.length > 0 && (
        <ul className="dg-rc__caveats" aria-label="Caveats">
          {caveats.map((caveat) => (
            // The producer's own token stays on the element: this surface has
            // no receipt sheet, so without the title the exact string the
            // pipeline emitted would be nowhere in the product.
            <li key={caveat} className="dg-rc__caveat" title={caveat}>
              {describeToken(caveat)}
            </li>
          ))}
        </ul>
      )}

      {blocked ? (
        <p className="dg-rc__blocked">
          This capacity read was blocked, so there are no numbers to show — not zero
          cuts required, no reading at all.
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

          {/* REVIEW-PANEL FIX — THE BLOCKER. This read "Sorted most expendable
              first — if you have to cut someone, start at the top", which is not
              true of the rows that actually sit at the top, and it is the one
              line on this surface a manager would act on.

              What the order really is (src/dynasty_genius/roster_cut_engine.py):
                · `forced_candidates` are PREPENDED with cut_priority=0 (:288-300)
                  — IR/reserve compliance problems, ordered for roster legality.
                  An injured star in an illegal reserve slot leads the list.
                · the rest sort by `_tier_sort_key` (:171-180), whose PRIMARY key
                  is the data-availability tier from `_scoring_tier` (:161-168):
                  A = we have an xVAR percentile, B = we have a dynasty value
                  score, C = neither, D = pre-model. Value is only the SECONDARY
                  key. So every scored player — your best included — sorts ahead
                  of every unscored one.
              Neither the tier nor `candidate_source` is rendered in the table
              (name, position, cut exposure rank, xVAR), so nothing else on screen
              corrects the sentence: it has to be true on its own. The retired
              string ("…as diagnostic order — not a cut sequence.") existed to
              forbid exactly the reading the replacement asserted. */}
          <p className="dg-rc__sort-basis">
            Ordered by what we know, not by who to drop: anyone with a roster-legality
            problem comes first, then the players we have a score for — lowest score at
            the top — and last the ones we can't score yet.
          </p>

          {(data.candidates ?? []).length === 0 ? (
            <p className="dg-rc__empty">No capacity candidates.</p>
          ) : (
            // DG-117: four columns fit 390px today, but the cut list is the
            // one table a manager reads on a phone before kickoff and it must
            // never be the thing that takes the page sideways.
            <TableScroll label="Cut candidates">
              <table className="dg-rc__table">
                <thead>
                  <tr className="dg-rc__row">
                    <th scope="col">Player</th>
                    <th scope="col">Pos</th>
                    <th scope="col">Cut exposure rank</th>
                    {/* DG-117: the bare acronym, on David's cut list. */}
                    <th scope="col">{fieldLabel("xvar")}</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.candidates ?? []).map((c) => (
                    <tr key={c.sleeper_player_id} className="dg-rc__row">
                      <td>
                        {/* DG-110: the cut list names players and had no way to
                          open one of them. */}
                        <PlayerNameButton
                          sleeperId={c.sleeper_player_id}
                          name={c.full_name}
                          context={c.position ?? undefined}
                          className="dg-rc__name"
                        />
                      </td>
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
            </TableScroll>
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
