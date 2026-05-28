#!/usr/bin/env python3.14
"""Build the MFL rookie ADP divergence report (read-only over model output).

Reads prospect_cards.json + MFL rookie ADP (read-only Sleeper) and writes a standalone
divergence artifact. Never mutates model/PVO state; writes only the divergence files.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

from src.dynasty_genius.adapters.mfl_adp_adapter import (  # noqa: E402
    _current_season,
    fetch_rookie_adp_rows,
)
from src.dynasty_genius.mfl_rookie_adp_divergence import (  # noqa: E402
    build_mfl_rookie_adp_divergence,
    write_mfl_rookie_adp_divergence_artifacts,
)

_CARDS_PATH = _ROOT / "resources" / "prospect_cards.json"
_OUTPUT_DIR = _ROOT / "app" / "data" / "valuation"


def _fetch_rows(season: int):
    """Seam: live read-only MFL fetch (monkeypatched in tests)."""
    return fetch_rookie_adp_rows(season)


def main(season: int | None = None, output_dir: Path | None = None) -> dict:
    season = season or _current_season()
    output_dir = Path(output_dir) if output_dir is not None else _OUTPUT_DIR
    rows, caveats = _fetch_rows(season)
    cards = json.loads(_CARDS_PATH.read_text())  # read-only
    captured_at = datetime.now(timezone.utc).isoformat()
    divergence = build_mfl_rookie_adp_divergence(
        rows, cards, season=season, captured_at=captured_at, caveats=caveats,
    )
    paths = write_mfl_rookie_adp_divergence_artifacts(
        divergence, output_dir=output_dir, run_id=f"phase-b_{season}",
    )
    cov = divergence["coverage"]
    print(
        f"Wrote {paths['latest_json']}; matched={cov['matched_count']} "
        f"unmatched_adp={cov['unmatched_adp_count']} unmatched_model={cov['unmatched_model_count']} "
        f"ambiguous={cov['ambiguous_count']} model_rank_unavailable={cov['model_rank_unavailable_count']}"
    )
    return divergence


if __name__ == "__main__":
    main()
