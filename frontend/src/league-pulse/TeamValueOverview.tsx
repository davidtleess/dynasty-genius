import type { LeaguePulseTeamValue } from "../lib/api";
import { fieldLabel, valueWord } from "../lib/copy";

// Team Value Overview — compact descriptive context. Strict per-field allowlists;
// NO raw player list (Inc1 excludes it); unknown nested keys + non-skill positions
// suppressed.
//
// DG-109: every allowlisted key is now a labelled pair in words, and the
// positional line reads as a sentence instead of `QB z_score -0.82 deficit`.
// The allowlists and the suppression rules are untouched.

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

/**
 * A pick field's value: the two counts are numbers, `pick_value_status` is an
 * enum that has to speak. Absence renders nothing rather than the string
 * "null".
 */
function pickValue(key: string, raw: unknown): string | null {
  if (raw === null || raw === undefined) return null;
  return key === "pick_value_status" ? valueWord(String(raw)) : String(raw);
}

function Pair({ label, value }: { label: string; value: string }) {
  return (
    <div className="dg-league-pulse__pair">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function ValueCard({ value }: { value: LeaguePulseTeamValue }) {
  const views = value.value_views as unknown as Record<string, unknown>;
  const age = value.age_profile as Record<string, number>;
  const picks = value.future_picks as Record<string, unknown>;
  const positional = value.positional_summary as Record<string, unknown>;

  return (
    <article className="dg-league-pulse__value-card">
      <h4 className="dg-league-pulse__value-name" data-user-text>
        {value.team_name ?? "Unknown team"}
      </h4>
      <p className="dg-league-pulse__value-roster">Roster {value.roster_id}</p>

      <dl className="dg-league-pulse__value-views">
        {VALUE_VIEW_KEYS.filter((k) => k in views).map((k) => (
          <Pair key={k} label={fieldLabel(k)} value={String(views[k])} />
        ))}
      </dl>

      <dl className="dg-league-pulse__value-age">
        {AGE_KEYS.filter((k) => k in age).map((k) => (
          <Pair key={k} label={fieldLabel(k)} value={String(age[k])} />
        ))}
      </dl>

      <dl className="dg-league-pulse__value-picks">
        {PICK_KEYS.filter((k) => k in picks).map((k) => {
          const shown = pickValue(k, picks[k]);
          return shown === null ? null : (
            <Pair key={k} label={fieldLabel(k)} value={shown} />
          );
        })}
      </dl>

      <ul className="dg-league-pulse__value-positions">
        {POSITIONS.map((position) => {
          const entry = positional[position];
          if (!entry || typeof entry !== "object") return null;
          const fields = entry as Record<string, unknown>;
          const z = fields.z_score;
          if (typeof z !== "number") return null;
          const depth = fields.surplus_label;
          return (
            <li key={position}>
              {`${position}: ${z.toFixed(2)} ${fieldLabel("z_score")}`}
              {typeof depth === "string" ? ` — ${valueWord(depth).toLowerCase()}` : ""}
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
