"""BUILD-4 T4 — qb_v3 research-output packaging (NOT a serving artifact).

Implements the ratified BUILD-4 spec §8 packaging under the T3 verdict: the
candidate promoted on NO horizon, so this artifact is research-only. Eligible
QBs carry per-horizon survival probabilities WITH the mandatory uncalibrated
caveat and the cohort-prior baseline rendered alongside (the transparency
patch: the model's adjustment off the capital+age prior is always visible);
abstained QBs carry NO model probability — only their disclosed reason and
band base rate. ``decision_supported=False`` recursively; no verdict fields,
no tier labels, no serving/PVO integration (a promotion would be its own
David-gated build).
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

ARTIFACT_STATUS = "research_only_not_promoted"

# Fork-A prior scalar → capital band (mirrors DRAFT_CAPITAL_PRIOR_BANDS in
# qb_v3_candidate_matrix.py; the scalar is the registered rule's output).
# Resolution is tolerance-based (float drift through the pipeline must not
# silently reclassify a band) and an unknown scalar FAILS CLOSED (Codex T4
# review: a public packaging seam never quietly falls to a default band).
CAPITAL_BAND_BY_PRIOR_SCALAR = {
    1.0: "round_1",
    0.7: "round_2",
    0.15: "day3",
    0.05: "undrafted",
    0.0: "beyond_prior_window",
}


def _resolve_capital_band(prior_scalar: float) -> str:
    for registered, band in CAPITAL_BAND_BY_PRIOR_SCALAR.items():
        if math.isclose(float(prior_scalar), registered, rel_tol=0.0, abs_tol=1e-9):
            return band
    raise ValueError(
        f"unknown draft_capital_prior scalar {prior_scalar!r}: not a registered "
        "fork-A band value — refusing to package under a guessed band"
    )


def build_qb_v3_research_output(
    *,
    candidate_matrix: pd.DataFrame,
    eligibility_mask: pd.DataFrame,
    probabilities: pd.DataFrame,
    cohort_priors: pd.DataFrame,
    validation_report: dict[str, Any],
    label_basis_disclosure: str,
) -> dict[str, Any]:
    """Compose the descriptive research artifact from the T2/T3 outputs."""
    _validate_inputs(candidate_matrix, eligibility_mask, probabilities, cohort_priors)

    mask = eligibility_mask.set_index(["player_id", "feature_season"])
    prior_lookup = {
        (row.capital_band, int(row.horizon)): float(row.base_rate_survival_prior)
        for row in cohort_priors.itertuples(index=False)
    }
    prob_lookup: dict[tuple[str, int], dict[int, float]] = {}
    for row in probabilities.itertuples(index=False):
        prob_lookup.setdefault((row.player_id, int(row.feature_season)), {})[
            int(row.horizon)
        ] = float(row.probability)

    rows: list[dict[str, Any]] = []
    for candidate in candidate_matrix.itertuples(index=False):
        key = (candidate.player_id, int(candidate.feature_season))
        mask_row = mask.loc[key]
        band = _resolve_capital_band(float(candidate.draft_capital_prior))
        if bool(mask_row["eligible_for_qb_v3_candidate"]):
            horizon_probabilities = prob_lookup.get(key, {})
            # Fail closed (Codex T4 review): an eligible row with no
            # probabilities, or a horizon without its cohort-prior baseline,
            # is a composition defect — never a silently thinner row.
            if not horizon_probabilities:
                raise ValueError(
                    f"eligible row {key} has no probability horizons to package"
                )
            by_horizon = {}
            for horizon, probability in sorted(horizon_probabilities.items()):
                if (band, horizon) not in prior_lookup:
                    raise ValueError(
                        f"missing cohort prior for band {band!r} horizon {horizon}"
                    )
                by_horizon[horizon] = {
                    "model_probability": probability,
                    "cohort_prior_baseline": prior_lookup[(band, horizon)],
                    "value_type": "probability_value",
                }
            rows.append(
                {
                    "player_id": candidate.player_id,
                    "feature_season": int(candidate.feature_season),
                    "eligibility_status": "eligible_for_research_probability",
                    "capital_band": band,
                    "survival_probabilities_by_horizon": by_horizon,
                    "caveats": ["uncalibrated_probability", "not_promoted_candidate"],
                    "decision_supported": False,
                }
            )
        else:
            # Abstained: no model probability anywhere in the row — only the
            # disclosed reason and the band's base rate (headline horizon 1).
            rows.append(
                {
                    "player_id": candidate.player_id,
                    "feature_season": int(candidate.feature_season),
                    "eligibility_status": "abstained",
                    "abstention_reason": mask_row["abstention_reason"],
                    "capital_band": band,
                    "base_rate_survival_prior": _headline_prior(prior_lookup, band),
                    "caveats": ["not_promoted_candidate"],
                    "decision_supported": False,
                }
            )

    # This builder packages the T3 verdict's research-only disposition; a
    # report claiming decision support or promotion eligibility is a different
    # artifact class and is REJECTED, never echoed inside a research shell
    # (Codex T4 review).
    if validation_report.get("decision_supported") is not False:
        raise ValueError("validation report must carry decision_supported=False")
    horizon_summary = validation_report.get("horizon_summary", {})
    if any(entry.get("promotion_eligible") for entry in horizon_summary.values()):
        raise ValueError(
            "validation report claims a promotion-eligible horizon: research-only "
            "packaging refuses it — a promoted artifact is a separate David-gated build"
        )
    return {
        "candidate_head": validation_report.get("candidate_head", "qb_v3_candidate"),
        "artifact_status": ARTIFACT_STATUS,
        "serving_integration": False,
        "pvo_integration": False,
        "label_basis_disclosure": label_basis_disclosure,
        "validation_summary": {
            int(horizon): {
                "promotion_eligible": bool(entry.get("promotion_eligible")),
                "non_promotion_reason": entry.get("non_promotion_reason"),
                "decision_supported": False,
            }
            for horizon, entry in horizon_summary.items()
        },
        "rows": rows,
        "decision_supported": False,
    }


def _validate_inputs(
    candidate_matrix: pd.DataFrame,
    eligibility_mask: pd.DataFrame,
    probabilities: pd.DataFrame,
    cohort_priors: pd.DataFrame,
) -> None:
    for name, frame, required in (
        ("candidate_matrix", candidate_matrix, ("player_id", "feature_season", "draft_capital_prior")),
        ("eligibility_mask", eligibility_mask, ("player_id", "feature_season", "eligible_for_qb_v3_candidate")),
        ("probabilities", probabilities, ("player_id", "feature_season", "horizon", "probability")),
        ("cohort_priors", cohort_priors, ("capital_band", "horizon", "base_rate_survival_prior")),
    ):
        for column in required:
            if column not in frame.columns:
                raise ValueError(f"{name} missing required column: {column}")
    if not pd.api.types.is_integer_dtype(candidate_matrix["feature_season"]):
        raise ValueError("candidate_matrix feature_season must be an integer season column")
    if candidate_matrix.duplicated(subset=["player_id", "feature_season"]).any():
        raise ValueError("duplicate candidate rows for (player_id, feature_season)")
    if probabilities.duplicated(subset=["player_id", "feature_season", "horizon"]).any():
        raise ValueError("duplicate probability rows for (player_id, feature_season, horizon)")
    if cohort_priors.duplicated(subset=["capital_band", "horizon"]).any():
        raise ValueError("duplicate cohort prior rows for (capital_band, horizon)")


def _headline_prior(
    prior_lookup: dict[tuple[str, int], float], band: str
) -> float:
    if (band, 1) not in prior_lookup:
        raise ValueError(f"missing headline (horizon 1) cohort prior for band {band!r}")
    return prior_lookup[(band, 1)]
