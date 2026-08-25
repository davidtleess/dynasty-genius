import type { z } from "zod";

import type { zPlayerDetailResponse } from "../lib/api/zod.gen";
import "./PlayerDetail.css";

type PlayerDetail = z.infer<typeof zPlayerDetailResponse>;
type FrozenPrediction = PlayerDetail["frozen_prediction"];

function stateLabel(frozen: FrozenPrediction): string {
  switch (frozen.status) {
    case "included":
      return `Included in ${frozen.season} model snapshot`;
    case "not_in_frozen_prediction_cohort":
      return `Not in ${frozen.season} model snapshot`;
    case "prediction_capture_incomplete":
      return `${frozen.season} prediction snapshot incomplete`;
    case "unavailable":
      return `${frozen.season} evaluation status unavailable`;
  }
}

export function FrozenPredictionStatus({
  frozen,
  compact = false,
}: {
  frozen: FrozenPrediction;
  compact?: boolean;
}) {
  const coverage = frozen.coverage;

  // Compact renders inline inside the inspector, which sits beside the full
  // card — a second region landmark named "<season> model evaluation" is an
  // axe landmark-unique violation, so only the full section is a landmark.
  if (compact) {
    return (
      <div className="dg-frozen-prediction dg-frozen-prediction--compact">
        <p className="dg-frozen-prediction__state">{stateLabel(frozen)}</p>
      </div>
    );
  }

  return (
    <section
      className="dg-frozen-prediction"
      aria-label={`${frozen.season} model evaluation`}
    >
      {!compact && (
        <p className="dg-frozen-prediction__eyebrow">{frozen.season} evaluation</p>
      )}
      <p className="dg-frozen-prediction__state">{stateLabel(frozen)}</p>
      {!compact && <p className="dg-frozen-prediction__message">{frozen.message}</p>}
      {!compact && coverage && (
        <p className="dg-frozen-prediction__coverage">
          {coverage.current_rostered_skill_in_frozen_prediction_cohort_count} of{" "}
          {coverage.current_rostered_skill_player_count} current rostered skill players
          were included.
        </p>
      )}
    </section>
  );
}
