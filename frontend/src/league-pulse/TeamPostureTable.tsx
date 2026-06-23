import { Fragment } from "react";

import type { LeaguePulseTeamPosture } from "../lib/api";

// Team Postures — compact descriptive context (contender / rebuilding / …).
// Strict component allowlist; unknown keys suppressed.

const COMPONENT_KEYS = [
  "starter_weighted_xvar_z",
  "age_window_score",
  "early_pick_balance_score",
  "development_stash_score",
] as const;

function PostureCard({ posture }: { posture: LeaguePulseTeamPosture }) {
  const components = posture.components as Record<string, number>;
  return (
    <article className="dg-league-pulse__posture-card">
      <h4 className="dg-league-pulse__posture-name">
        {posture.team_name ?? "Unknown team"}
      </h4>
      <p className="dg-league-pulse__posture-roster">Roster {posture.roster_id}</p>
      <p className="dg-league-pulse__posture-label">{posture.posture_label}</p>
      <p className="dg-league-pulse__posture-score">{posture.score.toFixed(3)}</p>
      <dl className="dg-league-pulse__posture-components">
        {COMPONENT_KEYS.map((k) => {
          const value = components[k];
          return typeof value === "number" ? (
            <Fragment key={k}>
              <dt>{k}</dt>
              <dd>{value.toFixed(2)}</dd>
            </Fragment>
          ) : null;
        })}
      </dl>
      <ul className="dg-league-pulse__posture-caveats">
        {(posture.caveats ?? []).map((c) => (
          <li key={c}>{c}</li>
        ))}
      </ul>
    </article>
  );
}

export function TeamPostureTable({ postures }: { postures: LeaguePulseTeamPosture[] }) {
  return (
    <section aria-label="Team Postures" className="dg-league-pulse__postures">
      <h3 className="dg-league-pulse__section-heading">Team Postures</h3>
      {postures.length === 0 ? (
        <p className="dg-league-pulse__empty">No team posture context available.</p>
      ) : (
        postures.map((posture) => (
          <PostureCard key={posture.roster_id} posture={posture} />
        ))
      )}
    </section>
  );
}
