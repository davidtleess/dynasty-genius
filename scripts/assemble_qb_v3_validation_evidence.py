"""BUILD-4 T5 — assemble the promotion-decision evidence snapshot.

Reproducibly regenerates docs/validation/build4_qb_v3_validation_evidence_v1.json:
the full T3 walk-forward validation report + generation metadata + the real
cohort-prior table (registered fork-A pick bands over the regenerated label
table, NFL-years-1-3 window, conditioned on the games>=4 feature floor).
Referenced by docs/validation/2026-07-04-build4-qb-v3-promotion-decision-record.md.

Run: .venv/bin/python3.14 scripts/assemble_qb_v3_validation_evidence.py
"""

from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.generate_qb_role_occupancy_labels import (
    FEATURE_STORE_PATH,
    _load_source_frames,
    build_qb_role_occupancy_labels_from_frames,
)
from scripts.generate_qb_v3_validation_report import (
    _load_draft_prior_rows,
    build_qb_v3_validation_report_from_frames,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = REPO_ROOT / "docs" / "validation" / "build4_qb_v3_validation_evidence_v1.json"
GENERATION_COMMAND = ".venv/bin/python3.14 scripts/assemble_qb_v3_validation_evidence.py"

PRIOR_WINDOW_NFL_YEARS = (1, 2, 3)
CAPITAL_BANDS = (
    (32, "round_1_picks_1_32"),
    (64, "round_2_picks_33_64"),
)
DAY3_BAND = "day3_picks_65_plus"
UNDRAFTED_BAND = "undrafted"


def _capital_band(draft_number: object) -> str:
    if pd.isna(draft_number):
        return UNDRAFTED_BAND
    slot = int(draft_number)
    for band_max, band in CAPITAL_BANDS:
        if slot <= band_max:
            return band
    return DAY3_BAND


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-out", type=Path, default=EVIDENCE_PATH)
    args = parser.parse_args()

    feature_store = pd.read_csv(FEATURE_STORE_PATH)
    feature_rows = feature_store[feature_store["position"] == "QB"]
    player_stats, snap_counts = _load_source_frames()
    draft_prior_rows = _load_draft_prior_rows()

    report = build_qb_v3_validation_report_from_frames(
        player_stats=player_stats,
        snap_counts=snap_counts,
        feature_rows=feature_rows,
        draft_prior_rows=draft_prior_rows,
    )

    labels = build_qb_role_occupancy_labels_from_frames(
        player_stats=player_stats,
        snap_counts=snap_counts,
        feature_rows=feature_rows,
    ).labels
    draft = draft_prior_rows.set_index("player_id")

    def band_for(player_id: str, feature_season: int) -> str | None:
        if player_id not in draft.index:
            return None
        entry_year = draft.loc[player_id, "entry_year"]
        nfl_year = int(feature_season) - int(entry_year) + 1
        if nfl_year not in PRIOR_WINDOW_NFL_YEARS:
            return None
        return _capital_band(draft.loc[player_id, "draft_number"])

    labels = labels.assign(
        capital_band=[
            band_for(player_id, season)
            for player_id, season in zip(
                labels["player_id"], labels["feature_season"], strict=True
            )
        ]
    )
    window = labels.dropna(subset=["capital_band"])
    table = (
        window.groupby(["capital_band", "horizon"])
        .agg(n=("startable_role_occupancy", "size"), positives=("startable_role_occupancy", "sum"))
        .reset_index()
    )
    table["survival_rate"] = (table["positives"] / table["n"]).round(3)

    repo_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    evidence = {
        "evidence_metadata": {
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            # Two distinct provenance contexts (Codex T5 R2): the T1-T4 machinery
            # that produced the run lives at machinery_repo_sha (HEAD at
            # generation); this assembly script itself is committed WITH the T5
            # decision record, so reproduction is from that commit or later.
            "machinery_repo_sha": repo_sha,
            "generation_command": GENERATION_COMMAND,
            "reproducible_from": "the T5 decision-record commit (which adds this script) or later",
            "random_state": report["random_state"],
            "source_caveat": (
                "nflreadpy source snapshot as of generation date; 2025-season data may "
                "still shift as the season finalizes — this evidence is a point-in-time "
                "record, not a live feed."
            ),
            "artifact_status": "validation_evidence_snapshot — not a deployment artifact",
            "label_row_count": int(len(labels)),
            "decision_supported": False,
        },
        "validation_report": report,
        "cohort_prior_table": {
            "population": (
                "labeled QB feature-seasons with NFL year 1-3 at feature time (the fork-A "
                "prior window), 2018-2023 feature seasons — CONDITIONED on the games>=4 "
                "feature floor: these are young QBs who actually played, not a full draft "
                "class; survival rates therefore embed an opportunity/selection effect"
            ),
            "band_definition": (
                "draft_number 1-32 / 33-64 / 65+ / undrafted (the registered fork-A pick bands)"
            ),
            "label_basis": (
                "startable_role_occupancy@H (games >= 8 AND snap_share >= 0.50; games_only "
                "fallback and conflations disclosed in the label diagnostics)"
            ),
            "note": (
                "evidence/baseline context — does NOT silently replace the registered T4 "
                "rookie-filter v1 priors (a different, unconditioned population); any prior "
                "update is a separate David-gated change"
            ),
            "rows": table.to_dict("records"),
            "decision_supported": False,
        },
        "decision_supported": False,
    }
    args.evidence_out.parent.mkdir(parents=True, exist_ok=True)
    args.evidence_out.write_text(json.dumps(evidence, indent=2, default=str))
    print(f"evidence -> {args.evidence_out}")
    print(table.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
