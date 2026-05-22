"""Build Phase 17.3 Team Value Matrix artifacts."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.team_value_matrix import (  # noqa: E402
    build_team_value_matrix,
    write_team_value_matrix_artifacts,
)

UNIVERSE_PVO_PATH = ROOT / "app" / "data" / "valuation" / "universe_pvo_latest.json"
LEAGUE_SNAPSHOT_PATH = ROOT / "app" / "data" / "league_snapshots" / "sleeper_universe_snapshot_latest.json"
OUTPUT_DIR = ROOT / "app" / "data" / "valuation"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def main() -> None:
    matrix = build_team_value_matrix(
        universe_pvo=_load_json(UNIVERSE_PVO_PATH),
        league_snapshot=_load_json(LEAGUE_SNAPSHOT_PATH),
        captured_at=datetime.now(timezone.utc).isoformat(),
    )
    run_id = datetime.now(timezone.utc).strftime("phase17-3-%Y%m%dT%H%M%SZ")
    paths = write_team_value_matrix_artifacts(matrix, output_dir=OUTPUT_DIR, run_id=run_id)
    print(f"Wrote Phase 17.3 Team Value Matrix: {paths['matrix']}")


if __name__ == "__main__":
    main()
