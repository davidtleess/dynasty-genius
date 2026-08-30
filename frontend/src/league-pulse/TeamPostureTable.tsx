import type { LeaguePulseTeamPosture } from "../lib/api";
import { fieldLabel, valueWord } from "../lib/copy";
import { TokenNotes } from "../ui/TokenNotes";

// Team Postures — compact descriptive context (contending / rebuilding / …).
// Strict component allowlist; unknown keys suppressed.
//
// DG-109: the four component names and the posture label all go through the
// copy dictionary. The allowlist, the suppression of unknown keys and the
// two-decimal precision are unchanged — only the words are.

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
      {/* The manager named their own team; the dictionary does not rename it. */}
      <h4 className="dg-league-pulse__posture-name" data-user-text>
        {posture.team_name ?? "Unknown team"}
      </h4>
      <p className="dg-league-pulse__posture-roster">Roster {posture.roster_id}</p>
      <p className="dg-league-pulse__posture-label" data-posture-neutral="true">
        {valueWord(posture.posture_label)}
      </p>
      <p className="dg-league-pulse__posture-score">{posture.score.toFixed(3)}</p>
      <dl className="dg-league-pulse__posture-components">
        {COMPONENT_KEYS.map((k) => {
          const value = components[k];
          return typeof value === "number" ? (
            <div key={k} className="dg-league-pulse__component-row">
              <dt>{fieldLabel(k)}</dt>
              <dd>{value.toFixed(2)}</dd>
            </div>
          ) : null;
        })}
      </dl>
      <TokenNotes
        className="dg-league-pulse__posture-caveats"
        tokens={posture.caveats ?? []}
      />
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
