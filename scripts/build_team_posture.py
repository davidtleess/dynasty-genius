"""Build Phase 18.3 team posture artifacts."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dynasty_genius.team_posture import (  # noqa: E402
    build_team_posture_artifact,
    write_team_posture_artifacts,
)

TEAM_MATRIX_PATH = ROOT / "app" / "data" / "valuation" / "team_value_matrix_latest.json"
OUTPUT_DIR = ROOT / "app" / "data" / "valuation"


def main() -> None:
    team_matrix = json.loads(TEAM_MATRIX_PATH.read_text())
    posture = build_team_posture_artifact(
        team_matrix,
        captured_at=datetime.now(timezone.utc).isoformat(),
    )
    run_id = datetime.now(timezone.utc).strftime("phase18-3-%Y%m%dT%H%M%SZ")
    paths = write_team_posture_artifacts(posture, output_dir=OUTPUT_DIR, run_id=run_id)
    print(f"Wrote Phase 18.3 team posture artifact: {paths['posture']}")


if __name__ == "__main__":
    main()
