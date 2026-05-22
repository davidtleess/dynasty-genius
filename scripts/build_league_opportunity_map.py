"""Build Phase 17.5 league opportunity map artifacts."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.league_opportunity_map import (  # noqa: E402
    build_league_opportunity_map,
    write_league_opportunity_artifacts,
)

TEAM_MATRIX_PATH = ROOT / "app" / "data" / "valuation" / "team_value_matrix_latest.json"
MARKET_DIVERGENCE_PATH = ROOT / "app" / "data" / "valuation" / "universe_market_divergence_latest.json"
OUTPUT_DIR = ROOT / "app" / "data" / "valuation"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def main() -> None:
    opportunity_map = build_league_opportunity_map(
        _load_json(TEAM_MATRIX_PATH),
        _load_json(MARKET_DIVERGENCE_PATH),
        perspective_roster_id=1,
        captured_at=datetime.now(timezone.utc).isoformat(),
    )
    run_id = datetime.now(timezone.utc).strftime("phase17-5-%Y%m%dT%H%M%SZ")
    paths = write_league_opportunity_artifacts(opportunity_map, output_dir=OUTPUT_DIR, run_id=run_id)
    print(f"Wrote Phase 17.5 league opportunity map: {paths['batch']}")
    print(f"Wrote Phase 17.5 league opportunity markdown: {paths['markdown']}")


if __name__ == "__main__":
    main()
