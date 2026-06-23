import { Fragment } from "react";

import type { LeaguePulseTeamValue } from "../lib/api";

// Team Value Overview — compact descriptive context. Strict per-field allowlists;
// NO raw player list (Inc1 excludes it); unknown nested keys + non-skill positions
// suppressed.

const VALUE_VIEW_KEYS = [
  "starter_weighted_xvar",
  "lineup_xvar",
  "depth_credit_xvar",
  "total_xvar_capped",
  "top_n_xvar",
] as const;

const AGE_KEYS = ["value_weighted_age", "median_age", "pct_value_over_28"] as const;

const PICK_KEYS = ["owned_count", "outgoing_count", "pick_value_status"] as const;

const POSITIONS = ["QB", "RB", "WR", "TE"] as const;

function ValueCard({ value }: { value: LeaguePulseTeamValue }) {
  const views = value.value_views as unknown as Record<string, unknown>;
  const age = value.age_profile as Record<string, number>;
  const picks = value.future_picks as Record<string, unknown>;
  const positional = value.positional_summary as Record<string, unknown>;

  return (
    <article className="dg-league-pulse__value-card">
      <h4 className="dg-league-pulse__value-name">
        {value.team_name ?? "Unknown team"}
      </h4>
      <p className="dg-league-pulse__value-roster">Roster {value.roster_id}</p>

      <dl className="dg-league-pulse__value-views">
        {VALUE_VIEW_KEYS.filter((k) => k in views).map((k) => (
          <Fragment key={k}>
            <dt>{k}</dt>
            <dd>{String(views[k])}</dd>
          </Fragment>
        ))}
      </dl>

      <dl className="dg-league-pulse__value-age">
        {AGE_KEYS.filter((k) => k in age).map((k) => (
          <Fragment key={k}>
            <dt>{k}</dt>
            <dd>{String(age[k])}</dd>
          </Fragment>
        ))}
      </dl>

      <dl className="dg-league-pulse__value-picks">
        {PICK_KEYS.filter((k) => k in picks).map((k) => (
          <Fragment key={k}>
            <dt>{k}</dt>
            <dd>{String(picks[k])}</dd>
          </Fragment>
        ))}
      </dl>

      <ul className="dg-league-pulse__value-positions">
        {POSITIONS.map((position) => {
          const entry = positional[position];
          if (!entry || typeof entry !== "object") return null;
          const fields = entry as Record<string, unknown>;
          const z = fields.z_score;
          if (typeof z !== "number") return null;
          return (
            <li key={position}>
              {position} z_score {z.toFixed(2)} {String(fields.surplus_label ?? "")}
            </li>
          );
        })}
      </ul>
    </article>
  );
}

export function TeamValueOverview({ values }: { values: LeaguePulseTeamValue[] }) {
  return (
    <section aria-label="Team Value Overview" className="dg-league-pulse__values">
      <h3 className="dg-league-pulse__section-heading">Team Value Overview</h3>
      {values.length === 0 ? (
        <p className="dg-league-pulse__empty">No team value context available.</p>
      ) : (
        values.map((value) => <ValueCard key={value.roster_id} value={value} />)
      )}
    </section>
  );
}
