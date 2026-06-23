"""Build Phase 17.5 league opportunity map artifacts."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pydantic import ValidationError  # noqa: E402

from src.dynasty_genius.league_opportunity_map import (  # noqa: E402
    build_league_opportunity_map,
    write_league_opportunity_artifacts,
)
from src.dynasty_genius.roster_cut_engine import RosterCutResult  # noqa: E402

TEAM_MATRIX_PATH = ROOT / "app" / "data" / "valuation" / "team_value_matrix_latest.json"
MARKET_DIVERGENCE_PATH = ROOT / "app" / "data" / "valuation" / "universe_market_divergence_latest.json"
TEAM_POSTURE_PATH = ROOT / "app" / "data" / "valuation" / "team_posture_latest.json"
ROSTER_CUT_REPORT_PATH = ROOT / "app" / "data" / "valuation" / "roster_cut_report_latest.json"
OUTPUT_DIR = ROOT / "app" / "data" / "valuation"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _load_roster_cut_result(path: Path) -> RosterCutResult:
    """Unwrap the report wrapper {run_id, captured_at, roster_cut_report} into the
    inner RosterCutResult. Fail closed (ValueError) on a missing/malformed inner
    object — no inline-engine fallback (F1)."""
    payload = json.loads(Path(path).read_text())
    if "roster_cut_report" not in payload:
        raise ValueError("roster_cut_report key missing from report wrapper")
    try:
        return RosterCutResult.model_validate(payload["roster_cut_report"])
    except ValidationError as exc:
        raise ValueError(f"malformed roster_cut_report inner object: {exc}") from exc


def main() -> None:
    team_posture = _load_json(TEAM_POSTURE_PATH) if TEAM_POSTURE_PATH.exists() else None
    roster_cut_result = _load_roster_cut_result(ROSTER_CUT_REPORT_PATH)
    opportunity_map = build_league_opportunity_map(
        _load_json(TEAM_MATRIX_PATH),
        _load_json(MARKET_DIVERGENCE_PATH),
        team_posture=team_posture,
        perspective_roster_id=1,
        captured_at=datetime.now(timezone.utc).isoformat(),
        roster_cut_result=roster_cut_result,
    )
    run_id = datetime.now(timezone.utc).strftime("phase17-5-%Y%m%dT%H%M%SZ")
    paths = write_league_opportunity_artifacts(opportunity_map, output_dir=OUTPUT_DIR, run_id=run_id)
    print(f"Wrote Phase 17.5 league opportunity map: {paths['batch']}")
    print(f"Wrote Phase 17.5 league opportunity markdown: {paths['markdown']}")


if __name__ == "__main__":
    main()
